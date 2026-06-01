import asyncio
import datetime
import logging
import sys

from automation_server_client import (
    AutomationServer,
    Workqueue,
    WorkItemError,
    Credential,
    WorkItemStatus,
)
from momentum_client.manager import MomentumClientManager
from odk_tools.tracking import Tracker
from sbsys.manager import SbsysClientManager

tracker: Tracker
momentum: MomentumClientManager
sbsys: SbsysClientManager
proces_navn = "Kontrolgruppen - Orientering af beskæftigelse - Fjern markering"

MARKERINGSNAVN = "Igangværende kontrolgruppe sag"
SAGSTITLER = [
    "Adresse - Kontrolgruppen",
    "Kontrolsager fra Udbetaling Danmark - Kontrolgruppen",
    "Samliv - Kontrolgruppen",
    "Sort arbejde - Kontrolgruppen",
    "Udrejse - Kontrolgruppen",
    "Øvrige kontrolsager - Kontrolgruppen",
]


async def populate_queue(workqueue: Workqueue):
    logger = logging.getLogger(__name__)

    logger.info("Populating queue...")

    tag = momentum.borgere.hent_markering(MARKERINGSNAVN)
    if tag is None:
        logger.error(f"Markeringen '{MARKERINGSNAVN}' findes ikke i Momentum.")
        return

    filters = [
        {
            "customFilter": "active",
            "fieldName": "tags/id",
            "values": [
                None,
                None,
                None,
                None,
                tag["id"]],
        }
    ]
    borgere = momentum.borgere.hent_borgere(filters=filters)

    for borger in borgere["data"]:
        workqueue.add_item(data={"cpr": borger["cpr"]}, reference=borger["cpr"])


async def process_workqueue(workqueue: Workqueue):
    logger = logging.getLogger(__name__)

    logger.info("Processing workqueue!")

    async with sbsys:
        liste_af_skabelons_id = []
        skabeloner = await sbsys.sagsskabeloner.hent_sagsskabeloner()
        for sagstitel in SAGSTITLER:
            skabelon = next((s for s in skabeloner if s["SagsTitel"].lower() == sagstitel.lower()), None)
            if skabelon:
                liste_af_skabelons_id.append(skabelon["Id"])
            else:
                logger.warning(f"Skabelon med titel '{sagstitel}' ikke fundet.")

        for item in workqueue:
            with item:
                data = item.data

                try:
                    cpr = data["cpr"]
                    # add dash to cpr if not present
                    if len(cpr) == 10 and "-" not in cpr:
                        cpr = cpr[:6] + "-" + cpr[6:]

                    aktive_sager = await sbsys.sager.søg_sager(
                        {
                            "SagsStatusIds": [
                                6
                            ],
                            "PrimaerPerson":{
                                "CprNummer":cpr
                            },
                            "SagsSkabeloner":
                                liste_af_skabelons_id
                        }
 
                    )

                    if aktive_sager:
                        continue

                    borger = momentum.borgere.hent_borger(cpr)
                    borgers_markeringer = momentum.borgere.hent_markeringer(borger)
                    markering = next(
                        (
                            m for m in borgers_markeringer
                            if m["tag"]["title"].lower() == MARKERINGSNAVN.lower() and m["end"] is None
                        ),
                        None,
                    )

                    if markering:
                        momentum.borgere.afslut_markering(
                            markering=markering,
                            slut_dato=datetime.datetime.today(),
                        )
                        tracker.track_task(proces_navn)

                except WorkItemError as e:
                    logger.error("Fejl ved behandling af arbejdselement.")
                    item.fail(str(e))


if __name__ == "__main__":
    ats = AutomationServer.from_environment()

    workqueue = ats.workqueue()

    tracking_credential = Credential.get_credential("Odense SQL Server")
    tracker = Tracker(
        username=tracking_credential.username, password=tracking_credential.password
    )
    momentum_credential = Credential.get_credential("Momentum - produktion")
    momentum = MomentumClientManager(
        base_url=momentum_credential.data["base_url"],
        client_id=momentum_credential.username,
        client_secret=momentum_credential.password,
        api_key=momentum_credential.data["api_key"],
        resource=momentum_credential.data["resource"],
    )
    sbsys_credential = Credential.get_credential("SBSYS - produktion")
    sbsys = SbsysClientManager(
        sbsys_credential.data["base_url"],
        sbsys_credential.data["token_url"],
        sbsys_credential.data["client_id"],
        sbsys_credential.data["client_secret"],
        sbsys_credential.username,
        sbsys_credential.password,
    )

    if "--queue" in sys.argv:
        workqueue.clear_workqueue(WorkItemStatus.NEW)
        asyncio.run(populate_queue(workqueue))
        exit(0)

    asyncio.run(process_workqueue(workqueue))
