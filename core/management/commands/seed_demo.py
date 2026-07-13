from datetime import date

from django.core.management.base import BaseCommand

from accounts.models import Role, User
from achats.models import Approbation, CircuitDemande, DemandeAchat, StatutDemande, TypeAchat
from core.models import Correspondant, Service
from courrier.models import Courrier, StatutCourrier, TypeCourrier, Urgence
from marches.models import Marche, StatutMarche, TypeProcedure


class Command(BaseCommand):
    help = (
        "Crée les services, les comptes de démonstration et une dizaine "
        "d'exemples réalistes (courriers liés, demandes d'achat des deux "
        "circuits, marchés) pour illustrer l'utilité de l'application."
    )

    def handle(self, *args, **options):
        # ------------------------------------------------------------ services
        services = {}
        for nom, code in [
            ("Direction Générale", "DG"),
            ("Service Achat", "ACHAT"),
            ("Service Financier", "FIN"),
            ("Service Informatique", "INFO"),
            ("Service Travaux", "TRAVAUX"),
        ]:
            service, _ = Service.objects.get_or_create(code=code, defaults={"nom": nom})
            services[code] = service

        # ------------------------------------------------------- utilisateurs
        users = [
            ("admin", Role.ADMINISTRATEUR, "DG", True),
            ("agent.bo", Role.AGENT_BUREAU_ORDRE, "DG", False),
            ("chef.info", Role.CHEF_SERVICE, "INFO", False),
            ("directeur", Role.DIRECTEUR, "DG", False),
            ("service.achat", Role.SERVICE_ACHAT, "ACHAT", False),
            ("service.financier", Role.SERVICE_FINANCIER, "FIN", False),
            ("audit", Role.AUDIT, "DG", False),
        ]
        created_users = {}
        for username, role, service_code, is_superuser in users:
            user, created = User.objects.get_or_create(
                username=username,
                defaults={
                    "role": role,
                    "service": services[service_code],
                    "is_staff": True,
                    "is_superuser": is_superuser,
                },
            )
            if created:
                user.set_password("Demo1234!")
                user.save()
                self.stdout.write(f"Utilisateur créé : {username} / Demo1234! (rôle : {role})")
            created_users[username] = user

        agent_bo = created_users["agent.bo"]

        # ------------------------------------------------------ correspondants
        for nom in [
            "Ministère de l'Équipement",
            "Gouvernorat",
            "Municipalité",
            "Direction Générale",
            "STEG",
            "SONEDE",
            "Société TunisiaBTP",
            "Société InfoTech Solutions",
            "Papeterie du Centre",
            "Société Gardiennage Sécurité Plus",
        ]:
            Correspondant.objects.get_or_create(nom=nom)

        # ---------------------------------------------------------- courriers
        def courrier(objet, **kwargs):
            defaults = dict(created_by=agent_bo, service=services["DG"])
            defaults.update(kwargs)
            obj, created = Courrier.objects.get_or_create(objet=objet, defaults=defaults)
            if created:
                obj.log_action(agent_bo, "Enregistrement", "Courrier enregistré au bureau d'ordre")
            return obj

        c_rapport = courrier(
            "Demande du rapport d'activité du premier trimestre 2026",
            type_courrier=TypeCourrier.ENTRANT, date_courrier=date(2026, 4, 6),
            emetteur="Ministère de l'Équipement", recepteur="Direction Générale",
            reference_externe="MEQ/DGA/2026/0891", urgence=Urgence.URGENT,
            statut=StatutCourrier.CLOTURE,
            resume="Le ministère demande la transmission du rapport d'activité trimestriel avant le 20 avril 2026.",
        )
        c_reunion = courrier(
            "Invitation à la réunion de coordination régionale du 15 juillet",
            type_courrier=TypeCourrier.ENTRANT, date_courrier=date(2026, 7, 2),
            emetteur="Gouvernorat", recepteur="Direction Générale",
            reference_externe="GOV/CAB/2026/1745", statut=StatutCourrier.EN_TRAITEMENT,
            resume="Réunion de coordination des services techniques régionaux, salle de conférence du gouvernorat.",
        )
        c_offre_btp = courrier(
            "Offre pour la consultation relative aux travaux de réfection de la route régionale RR133",
            type_courrier=TypeCourrier.ENTRANT, date_courrier=date(2026, 5, 18),
            emetteur="Société TunisiaBTP", recepteur="Service Travaux",
            reference_externe="TBTP/2026/077", statut=StatutCourrier.TRANSMIS,
            service=services["TRAVAUX"],
            resume="Offre technique et financière pour les travaux de réfection de la RR133 sur 12 km.",
        )
        c_facture = courrier(
            "Facture d'électricité du deuxième trimestre 2026",
            type_courrier=TypeCourrier.ENTRANT, date_courrier=date(2026, 7, 7),
            emetteur="STEG", recepteur="Service Financier",
            reference_externe="STEG/2026/45120", statut=StatutCourrier.EN_ATTENTE,
            service=services["FIN"],
            remarque="À régler avant le 31 juillet pour éviter les pénalités.",
        )
        c_eclairage = courrier(
            "Demande d'intervention pour la réparation de l'éclairage public de l'avenue principale",
            type_courrier=TypeCourrier.ENTRANT, date_courrier=date(2026, 6, 25),
            emetteur="Municipalité", recepteur="Service Travaux",
            reference_externe="MUN/ST/2026/312", urgence=Urgence.URGENT,
            statut=StatutCourrier.EN_TRAITEMENT, service=services["TRAVAUX"],
            resume="Plusieurs points lumineux hors service ; risque pour la circulation nocturne.",
        )
        c_devis_info = courrier(
            "Devis pour le renouvellement du parc informatique",
            type_courrier=TypeCourrier.ENTRANT, date_courrier=date(2026, 6, 10),
            emetteur="Société InfoTech Solutions", recepteur="Service Informatique",
            reference_externe="ITS/DEV/2026/208", statut=StatutCourrier.ENREGISTRE,
            service=services["INFO"],
        )

        c_envoi_rapport = courrier(
            "Transmission du rapport d'activité du premier trimestre 2026",
            type_courrier=TypeCourrier.SORTANT, date_courrier=date(2026, 4, 17),
            emetteur="Direction Générale", recepteur="Ministère de l'Équipement",
            reference_externe="DTPCSSO/2026/0455", statut=StatutCourrier.CLOTURE,
            resume="Envoi du rapport trimestriel demandé par courrier MEQ/DGA/2026/0891.",
        )
        c_convocation = courrier(
            "Convocation des chefs de service à la réunion préparatoire du 12 juillet",
            type_courrier=TypeCourrier.SORTANT, date_courrier=date(2026, 7, 4),
            emetteur="Direction Générale", recepteur="Chefs de service",
            reference_externe="DTPCSSO/2026/0817", statut=StatutCourrier.ENREGISTRE,
            remarque="Préparation de la réunion de coordination régionale du gouvernorat.",
        )
        c_notif_btp = courrier(
            "Notification des résultats de la consultation travaux de réfection de la RR133",
            type_courrier=TypeCourrier.SORTANT, date_courrier=date(2026, 6, 12),
            emetteur="Service Travaux", recepteur="Société TunisiaBTP",
            reference_externe="DTPCSSO/2026/0702", statut=StatutCourrier.TRANSMIS,
            service=services["TRAVAUX"],
        )
        c_rep_eclairage = courrier(
            "Programmation de l'intervention éclairage public — avenue principale",
            type_courrier=TypeCourrier.SORTANT, date_courrier=date(2026, 7, 1),
            emetteur="Service Travaux", recepteur="Municipalité",
            reference_externe="DTPCSSO/2026/0801", statut=StatutCourrier.ENREGISTRE,
            service=services["TRAVAUX"],
            resume="Intervention programmée la semaine du 6 juillet ; équipe et nacelle mobilisées.",
        )

        # liaisons entre correspondances (question ↔ réponse)
        c_rapport.courriers_lies.add(c_envoi_rapport)
        c_offre_btp.courriers_lies.add(c_notif_btp)
        c_eclairage.courriers_lies.add(c_rep_eclairage)
        c_reunion.courriers_lies.add(c_convocation)

        # ---------------------------------------------------- demandes d'achat
        def demande(objet, **kwargs):
            defaults = dict(created_by=created_users["chef.info"])
            defaults.update(kwargs)
            obj, _ = DemandeAchat.objects.get_or_create(objet=objet, defaults=defaults)
            return obj

        d_bureau = demande(
            "Achat de fournitures de bureau pour le second semestre 2026",
            service_demandeur=services["DG"], circuit=CircuitDemande.LOCALE,
            type_achat=TypeAchat.FOURNITURES, montant_estimatif=3500,
            date_creation=date(2026, 6, 20), statut=StatutDemande.SIGNEE_DIRECTEUR,
            date_signature_directeur=date(2026, 7, 8),
            description="Papier, classeurs, consommables d'impression pour l'ensemble des services.",
        )
        d_info = demande(
            "Acquisition de 10 postes de travail informatiques",
            service_demandeur=services["INFO"], circuit=CircuitDemande.AVEC_ACCORDS,
            type_achat=TypeAchat.MATERIEL_INFORMATIQUE, montant_estimatif=15000,
            date_creation=date(2026, 6, 1), statut=StatutDemande.EN_ATTENTE_ACCORDS,
            description="Renouvellement des postes de travail obsolètes du service informatique (devis ITS/DEV/2026/208).",
        )
        d_clim = demande(
            "Maintenance annuelle des équipements de climatisation",
            service_demandeur=services["DG"], circuit=CircuitDemande.LOCALE,
            type_achat=TypeAchat.MAINTENANCE, montant_estimatif=4200,
            date_creation=date(2026, 5, 12), statut=StatutDemande.TRANSMISE_SERVICE_ACHAT,
            date_signature_directeur=date(2026, 5, 20),
            numero_ordre_bo="BO-DA-2026-00021", date_enregistrement_bo=date(2026, 5, 21),
        )
        d_route = demande(
            "Travaux de réfection de la route régionale RR133",
            service_demandeur=services["TRAVAUX"], circuit=CircuitDemande.AVEC_ACCORDS,
            type_achat=TypeAchat.TRAVAUX, montant_estimatif=850000,
            date_creation=date(2026, 3, 10), statut=StatutDemande.MARCHE_LANCE,
            date_signature_directeur=date(2026, 4, 2),
            numero_ordre_bo="BO-DA-2026-00012", date_enregistrement_bo=date(2026, 4, 3),
            description="Réfection de 12 km de chaussée dégradée, signalisation comprise.",
        )
        d_carburant = demande(
            "Approvisionnement en carburant des véhicules de service",
            service_demandeur=services["DG"], circuit=CircuitDemande.LOCALE,
            type_achat=TypeAchat.FOURNITURES, montant_estimatif=8000,
            date_creation=date(2026, 4, 15), statut=StatutDemande.CLOTUREE,
            date_signature_directeur=date(2026, 4, 22),
            numero_ordre_bo="BO-DA-2026-00015", date_enregistrement_bo=date(2026, 4, 23),
        )
        d_gardiennage = demande(
            "Prestations de gardiennage des locaux pour l'année 2027",
            service_demandeur=services["DG"], circuit=CircuitDemande.AVEC_ACCORDS,
            type_achat=TypeAchat.PRESTATIONS, montant_estimatif=36000,
            date_creation=date(2026, 6, 28), statut=StatutDemande.SOUMISE_DIRECTEUR,
        )

        d_info.demandes_liees.add(d_route)  # projets d'équipement de la même année

        if not d_route.approbations.exists():
            Approbation.objects.create(
                demande=d_route, valideur=created_users["directeur"],
                fonction="Directeur", decision=Approbation.Decision.APPROUVE,
                commentaire="Priorité régionale — accords DCP obtenus le 28/03/2026.",
            )
        if not d_gardiennage.approbations.exists():
            Approbation.objects.create(
                demande=d_gardiennage, valideur=created_users["chef.info"],
                fonction="Chef de service", decision=Approbation.Decision.APPROUVE,
                commentaire="Renouvellement du contrat arrivant à échéance en décembre.",
            )

        # ------------------------------------------------------------- marchés
        def marche(objet, **kwargs):
            defaults = dict(created_by=created_users["service.achat"])
            defaults.update(kwargs)
            obj, _ = Marche.objects.get_or_create(objet=objet, defaults=defaults)
            return obj

        m_route = marche(
            "Marché de travaux — réfection de la route régionale RR133",
            type_procedure=TypeProcedure.APPEL_OFFRES_OUVERT,
            service_demandeur=services["TRAVAUX"], demande_achat=d_route,
            fournisseur="Société TunisiaBTP", montant=812450,
            date_lancement=date(2026, 4, 10), date_attribution=date(2026, 6, 5),
            date_notification=date(2026, 6, 12), statut=StatutMarche.EN_COURS_EXECUTION,
        )
        m_info = marche(
            "Consultation — acquisition de 10 postes de travail informatiques",
            type_procedure=TypeProcedure.CONSULTATION,
            service_demandeur=services["INFO"], demande_achat=d_info,
            date_lancement=date(2026, 7, 1), statut=StatutMarche.ANALYSE_OFFRES,
        )
        m_bureau = marche(
            "Bon de commande — fournitures de bureau premier semestre 2026",
            type_procedure=TypeProcedure.BON_COMMANDE,
            service_demandeur=services["DG"],
            fournisseur="Papeterie du Centre", montant=2980,
            date_lancement=date(2026, 1, 15), date_cloture=date(2026, 2, 28),
            statut=StatutMarche.CLOTURE,
        )
        m_gardiennage = marche(
            "Marché de prestations — gardiennage des locaux 2027",
            type_procedure=TypeProcedure.APPEL_OFFRES_RESTREINT,
            service_demandeur=services["DG"], demande_achat=d_gardiennage,
            date_lancement=date(2026, 7, 5), statut=StatutMarche.CONSULTATION_LANCEE,
        )

        m_route.marches_lies.add(m_info)  # programme d'équipement 2026

        self.stdout.write(self.style.SUCCESS(
            f"Données de démonstration : {Courrier.objects.count()} courriers, "
            f"{DemandeAchat.objects.count()} demandes d'achat, {Marche.objects.count()} marchés."
        ))
