"""Nœud analyste : classification + résumé tracé (cf. docs/cadrage.md §2 et §8)."""

import html
import re
from collections.abc import Iterator
from dataclasses import dataclass, field

from langchain_anthropic import ChatAnthropic
from pydantic import BaseModel, Field, ValidationError

from backend.guardrails import BudgetExceeded, check_and_increment_llm_call
from backend.memory.store import mark_analyzed_as_seen
from backend.state import AnalyzedItem, Category, RawItem, VeilleState

MODEL = "claude-haiku-4-5-20251001"

SYSTEM_PROMPT = """Tu es un analyste de veille défense/géopolitique. Pour l'article fourni :
1. Classe-le dans une des catégories : export_control, contrat_armement, mouvement_militaire,
   diplomatie_defense, programme_industriel, ou hors_perimetre si l'article ne relève d'aucune
   de ces catégories (ex. actualité technologique générale, cybersécurité, analyse financière).
   Le filtrage est thématique uniquement — la localisation géographique de l'article n'entre pas
   en compte dans ce choix. Précisions de frontière :
   - Fusion-acquisition ou prise de participation dans l'industrie de défense : classe en
     programme_industriel si l'article porte sur l'opération elle-même (parties, montant, enjeu
     stratégique) ; en export_control seulement si l'article traite explicitement d'une licence,
     sanction ou embargo ; en hors_perimetre si l'article est centré sur l'analyse boursière (cours,
     réaction de marché) plutôt que sur l'opération.
   - Contenu d'opinion, tribune ou analyse prospective qui ne rapporte pas un fait ou événement daté
     et vérifiable : classe en hors_perimetre même si le thème correspond au périmètre. Un article
     qui rapporte un fait daté puis l'accompagne d'analyse reste inclus ; une simple prise de
     position n'est pas incluse.
   - diplomatie_defense vs mouvement_militaire : ce qui départage n'est pas la forme de l'acte
     rapporté mais son contenu. Un fait opérationnel accompli ou un état de fait établi (une force
     est déployée, un détroit est fermé ou sous contrôle, une frappe a eu lieu, un espace aérien est
     fermé) relève de mouvement_militaire — y compris, et surtout, quand il est rapporté par une
     déclaration ou un communiqué officiel : la déclaration n'est alors que la source qui établit le
     fait, elle n'est pas le sujet de l'article. Ne classe en diplomatie_defense que si ce qui est
     déclaré est une intention, une menace, une capacité revendiquée, une posture, une position de
     principe (ce qu'un État fera, pourrait faire, ou juge inacceptable) ou la coopération défense
     entre États — ainsi que le commentaire sur un déploiement, par opposition au déploiement
     lui-même. Un commandant déclarant qu'un détroit est fermé et sous son contrôle rapporte un fait
     accompli (mouvement_militaire) ; le même menaçant de le fermer énonce une intention
     (diplomatie_defense).
   - diplomatie_defense vs hors_perimetre : une déclaration ou un communiqué officiel attribué à un
     responsable nommé, sur la coopération, les alliances ou la posture défense/sécurité entre États,
     est un fait daté (pas une tribune) — ne classe pas en hors_perimetre au seul motif qu'aucun
     contrat ni mouvement n'est décrit. À l'inverse, une visite d'État, un message protocolaire ou
     une pression diplomatique générale (droits humains, politique intérieure d'un pays tiers) sans
     contenu défense/sécurité explicite reste hors_perimetre même si les deux pays ont par ailleurs
     une relation de défense.
2. Traduis le titre en français (title_fr), fidèlement, même si le titre original est déjà en français.
3. Rédige un résumé factuel en français, 2-3 phrases maximum, sans interprétation ni spéculation.
4. Fournis une citation : un extrait VERBATIM du texte source, dans sa langue d'origine (copié-collé
   exact, jamais traduit) qui justifie le résumé. Si aucun extrait ne justifie clairement le résumé,
   catégorise en hors_perimetre et laisse la citation vide.
5. Fournis location : le pays, la mer ou la région principale concernée par l'article, extrait
   VERBATIM du titre ou du texte source. Privilégie le nom de pays quand il est écrit tel quel.
   Laisse vide si aucun lieu n'est explicitement nommé — ne déduis jamais un lieu qui n'est pas
   écrit noir sur blanc, et ne transforme pas un gentilé en nom de pays (« Ukrainian » n'autorise
   pas « Ukraine » si le mot « Ukraine » n'apparaît nulle part).
6. Fournis location_country : le pays souverain dans lequel se trouve le lieu de location, en
   ANGLAIS et sous sa forme usuelle (« Australia », « Ukraine », « United States of America »).
   Contrairement aux champs précédents ce n'est PAS un extrait du texte : c'est la seule déduction
   autorisée, et elle ne sert qu'à placer l'item sur une carte par pays. « Darwin » donne
   « Australia », « Kharkiv » donne « Ukraine ». Laisse vide dans ces quatre cas :
   - location est vide (rien à rattacher) ;
   - le lieu n'appartient à aucun pays : haute mer, détroit international, espace, région
     transnationale (« Sahel », « Balkans »), organisation ou unité militaire ;
   - le lieu est dans plusieurs pays sans qu'un seul domine ;
   - la souveraineté du lieu est contestée ou ferait l'objet d'un désaccord entre États.
   Un champ vide est toujours préférable à un rattachement arbitré.
7. Fournis domestic : l'événement rapporté se situe-t-il dans le pays de la source, indiqué en tête
   du message ? Réponds d'après le contenu de l'article, jamais d'après la seule origine du média :
   couvrir l'étranger est le cas le plus fréquent, et un média qui rapporte un événement survenu
   dans un pays tiers doit donner false même si l'article est écrit depuis son propre pays.
   true correspond à l'actualité intérieure : institution, administration, industrie ou forces
   armées du pays de la source agissant sur son propre territoire. Dans le doute, false.
   Ce champ ne dispense pas de renseigner location et location_country : réponds aux trois."""


class _Analysis(BaseModel):
    category: Category = Field(description="Catégorie du périmètre MECE ou hors_perimetre (thématique uniquement)")
    title_fr: str = Field(description="Titre traduit en français, fidèle au titre original")
    summary: str = Field(description="Résumé factuel en français, 2-3 phrases maximum")
    citation: str = Field(description="Extrait verbatim du texte source, langue d'origine, justifiant le résumé")
    location: str = Field(
        description="Extrait verbatim nommant le pays/lieu principal de l'article ; vide si non mentionné"
    )
    location_country: str = Field(
        description="Pays souverain du lieu de location, nom anglais usuel ; vide si le lieu n'est dans aucun pays, "
        "est transnational ou de souveraineté contestée"
    )
    domestic: bool = Field(
        description="L'événement rapporté se situe-t-il dans le pays de la source ? false dès que l'article "
        "couvre l'étranger, et dans le doute"
    )


def _clean_text(raw_html: str) -> str:
    return html.unescape(re.sub(r"<[^>]+>", " ", raw_html)).strip()


def _normalize(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip().lower()


def _extract_verified(extract: str, source_text: str) -> bool:
    """Vérifie qu'un extrait (citation ou zone_evidence) est bien un verbatim du texte source."""
    return bool(extract.strip()) and _normalize(extract) in _normalize(source_text)


_llm = None

# Noms anglais des codes pays de backend/config.py, pour la question `domestic` : « RU » se lit
# mal, « Russia » non. "INT" (source multi-pays / institutionnelle UE) n'a pas de pays d'origine
# et est traité à part — la question n'a pas de sens pour ce cas.
_SOURCE_COUNTRY_NAME: dict[str, str] = {
    "US": "the United States",
    "FR": "France",
    "RU": "Russia",
    "CN": "China",
    "DE": "Germany",
    "IT": "Italy",
    "GB": "the United Kingdom",
    "IL": "Israel",
    "ES": "Spain",
    "KR": "South Korea",
    "IR": "Iran",
    "KP": "North Korea",
}


def classify_item(item: RawItem) -> _Analysis:
    """Appelle le LLM pour un item, sans filtrage. Réutilisé par analyze() et par l'éval (backend/eval/)."""
    global _llm
    if _llm is None:
        _llm = ChatAnthropic(model=MODEL, temperature=0).with_structured_output(_Analysis)

    clean_text = _clean_text(item["raw_text"])
    # Le pays de la source n'est donné que pour la question 7. Il est placé en tête et nommé comme
    # tel pour ne pas contaminer l'extraction de location, qui doit rester un verbatim du texte :
    # une source russe couvrant l'Ukraine ne doit pas se mettre à produire « Russia ».
    origin = _SOURCE_COUNTRY_NAME.get(item["country"], "an international or multi-country outlet")
    check_and_increment_llm_call()
    return _llm.invoke(
        [
            ("system", SYSTEM_PROMPT),
            (
                "human",
                f"Pays de la source (métadonnée, ne fait pas partie de l'article, à n'utiliser que "
                f"pour la question 7) : {origin}\n\nTitre : {item['title']}\n\nTexte : {clean_text}",
            ),
        ]
    )


@dataclass
class _Progress:
    """Ce que le nœud a réellement soumis au modèle, et s'il s'est arrêté avant la fin du lot.

    Mutable et partagé avec le générateur plutôt que renvoyé en fin d'itération : l'appelant doit
    pouvoir lire ces deux informations même si l'itération s'interrompt en cours de route.
    """

    # Les items dont le sort est réglé — retenus ou écartés. Inscrits dans la mémoire de
    # dédoublonnage en sortie de nœud, y compris si le nœud échoue en cours de route : ce qui a été
    # payé ne doit pas être repayé, ce qui n'a pas été traité doit rester collectable.
    submitted: list[RawItem] = field(default_factory=list)
    truncated: bool = False


def analyze(state: VeilleState) -> VeilleState:
    """Nœud LangGraph : classe et résume chaque raw_item, rejette les résumés non tracés."""
    analyzed_items: list[AnalyzedItem] = []
    progress = _Progress()
    try:
        analyzed_items.extend(_analyze_items(state["raw_items"], progress))
    finally:
        mark_analyzed_as_seen(progress.submitted)

    return {"analyzed_items": analyzed_items, "truncated": progress.truncated}


def _analyze_items(raw_items: list[RawItem], progress: _Progress) -> Iterator[AnalyzedItem]:
    """Générateur : `progress` se remplit au fil de la consommation, pour que l'appelant sache
    exactement ce qui a été soumis au modèle même si l'itération s'interrompt."""
    for item in raw_items:
        progress.submitted.append(item)
        try:
            result = classify_item(item)
        except BudgetExceeded:
            # Le plafond quotidien tronque le lot, il ne détruit pas le travail déjà payé : on cesse
            # d'itérer et on rend les items déjà analysés, que l'appelant enregistrera normalement.
            #
            # Cet item-ci, en revanche, n'a rien coûté : le plafond est vérifié *avant* l'appel
            # (backend/guardrails.py), qui n'a donc pas eu lieu. Le retirer des soumis est ce qui le
            # garde collectable demain — le laisser le ferait marquer « vu » sans avoir jamais été
            # analysé, exactement la perte que `mark_analyzed_as_seen` a été déplacé ici pour éviter.
            progress.submitted.pop()
            progress.truncated = True
            return
        except ValidationError:
            # Le modèle peut renvoyer une catégorie hors énumération — vu en conditions réelles sur
            # une source hispanophone (« diplomacia_defense » au lieu de « diplomatie_defense »).
            # Un item mal formé se traite comme un item non classable : on l'écarte, comme un résumé
            # sans citation vérifiable. Le faire remonter ferait perdre tout le run, y compris les
            # items déjà analysés avant lui — un coût sans rapport avec celui d'un item raté.
            # L'appel LLM a bien eu lieu : le budget (§8) est décompté, ici comme ailleurs.
            continue
        clean_text = _clean_text(item["raw_text"])

        if result.category == "hors_perimetre":
            continue
        if not _extract_verified(result.citation, clean_text):
            # Garde-fou traçabilité (docs/cadrage.md §8) : pas de citation vérifiable, pas de résumé.
            continue

        # location est une métadonnée pour la carte (docs/cadrage.md §4) : ne filtre pas la
        # collecte (pas de restriction géographique en V1), mais reste soumise au même garde-fou de
        # traçabilité que la citation — pas de lieu inventé, vide plutôt que non vérifiable.
        #
        # Le titre fait partie du texte vérifiable, contrairement à la citation qui doit justifier
        # le résumé et vient donc du corps. Mesuré sur un run réel : la vérification contre le seul
        # corps effaçait des extractions correctes, 10 des 11 lieux vides ayant leur pays nommé dans
        # le titre et nulle part ailleurs (les extraits RSS sont souvent tronqués, cf. §11).
        location = result.location if _extract_verified(result.location, f"{item['title']} {clean_text}") else ""

        # location_country est la seule sortie du LLM soustraite au garde-fou verbatim, parce
        # qu'elle est par construction absente du texte : « Darwin » ne contient pas « Australia ».
        # Deux contreparties la bornent. Ici : pas de lieu vérifié, pas de pays — sinon un lieu
        # rejeté au verbatim reviendrait par la porte de derrière placer l'item sur la carte.
        # À la restitution : le front ne retient ce pays que s'il existe dans le référentiel de la
        # carte, et le marque comme déduit (frontend/src/lib/geo.ts).
        location_country = result.location_country.strip() if location else ""

        # Repli de dernier recours pour les items sans aucun lieu nommé : le modèle a jugé, sur le
        # contenu de l'article, que l'événement se situe dans le pays de la source. Trois bornes.
        #
        # Il ne s'applique qu'à `location` vide : si un lieu a été extrait mais n'est rattachable à
        # aucun pays (« Black Sea »), c'est une réponse, pas un manque — la remplacer par le pays du
        # média serait une régression, pas un repli.
        #
        # Il est refusé aux sources "INT", qui n'ont pas de pays d'origine.
        #
        # Et il reste plus faible que `location_country`, qui déduit d'un lieu nommé : ici rien
        # n'est nommé, seul le contenu est jugé. La restitution le distingue donc en « présumé »,
        # et non en « déduit » (frontend/src/lib/geo.ts). Le pays de la source ne suffit jamais à
        # lui seul : sans ce jugement, un média d'État couvrant l'étranger gonflerait l'empreinte
        # de son propre pays, et le périmètre en sur-échantillonne délibérément (cf. §4).
        domestic_to_source = bool(result.domestic) and not location and item["country"] != "INT"

        yield AnalyzedItem(
            source=item["source"],
            lang=item["lang"],
            country=item["country"],
            state_affiliated=item["state_affiliated"],
            title=item["title"],
            title_fr=result.title_fr,
            link=item["link"],
            published=item["published"],
            category=result.category,
            summary=result.summary,
            citation=result.citation,
            location=location,
            location_country=location_country,
            domestic_to_source=domestic_to_source,
            confidence_score=None,
            corroborated=None,
        )
