"""Optional domain policies; no domain knowledge belongs in the list executor."""
from dataclasses import dataclass
import re


@dataclass(frozen=True)
class PropertyPolicy:
    name: str
    field: str
    vocabulary: frozenset[str]
    accepted: frozenset[str]
    aliases: tuple[tuple[str,str], ...]
    instructions: str

    def includes(self, row):
        value=row.get(self.field)
        if isinstance(value,str):
            value=dict(self.aliases).get(value.strip().casefold(),value.strip().casefold())
        if not isinstance(value,str) or value not in self.vocabulary:
            raise ValueError(f'{row.get("text")}: invalid {self.field}={value!r}; choose '+','.join(sorted(self.vocabulary)))
        return value in self.accepted


BOTANICAL_PARTS=PropertyPolicy(
    'botanical_nonfruit_parts','plant_part',
    frozenset(('root','tuber','bulb','stem','leaf','flower','fruit','seed','grain','processed','nonplant')),
    frozenset(('root','tuber','bulb','stem','leaf','flower')),
    (('roots','root'),('tubers','tuber'),('bulbs','bulb'),('stems','stem'),('leaves','leaf'),
     ('flowers','flower'),('fruits','fruit'),('seeds','seed'),('grains','grain'),('non-plant','nonplant')),
    'For this strict botanical vegetable task, give EVERY item plant_part from root,tuber,bulb,stem,leaf,flower,fruit,seed,grain,processed,nonplant. '
    'Identify the part actually consumed, not the whole plant or culinary label. A seed is NOT itself a fruit; a seed-containing pod is fruit. '
    'The program selects edible roots/tubers/bulbs/stems/leaves/flowers and excludes seeds/grains/fruits and processed/nonplant products. '
    'Do not invent exclusions for herbs or spices; classify their actual plant part.')

POLICIES={BOTANICAL_PARTS.name:BOTANICAL_PARTS}


def select_list_policy(question, enabled=True):
    """Conservative opt-in by task semantics; uncertain/culinary requests abstain."""
    if not enabled:return None
    q=question.casefold()
    explicit_exclusion=re.search(r'\b(?:no|exclude|excluding|without|not include)\b[^.!?\n]{0,50}\bbotanical fruits?\b',q)
    if explicit_exclusion and re.search(r'\bvegetables?\b',q) and not re.search(r'\b(?:culinary|cooking|everyday)\b',q):
        return BOTANICAL_PARTS.name
    return None


def wants_species_census(question):
    q=question.casefold()
    return bool(re.search(r'\bspecies\b',q) and re.search(r'simultaneous|same time',q)
                and re.search(r'how many|highest number|maximum number|largest number',q))


def historical_neighbor_year(question):
    """This strategy only supports numeric adjacent identifiers and surname output."""
    match=re.search(r'\bas of\s+(?:[A-Za-z]+\s+)?((?:19|20)\d{2})',question,re.I)
    applicable=(match and re.search(r'\bbefore\b.*\bafter\b',question,re.I)
                and re.search(r'\bnumber',question,re.I)
                and re.search(r'last names?|surnames?',question,re.I)
                and not re.search(r'nearest|occupied|available|alphabetic',question,re.I))
    return int(match[1]) if applicable else None
