from dataclasses import dataclass
from enum import StrEnum
from re import findall
from typing import Protocol


class LeadReviewCategory(StrEnum):
    STRONG_CANDIDATE = 'Strong Candidate'
    NEEDS_REVIEW = 'Needs Review'
    HIGHER_RISK = 'Higher Risk / Human Review Required'


@dataclass(frozen=True)
class LeadScoreResult:
    score: int
    category: LeadReviewCategory
    positive_factors: tuple[str, ...]
    negative_factors: tuple[str, ...]


class ScorableLead(Protocol):
    interested_in_public_work: bool | None
    bankruptcies: bool | None
    foreclosures: bool | None
    tax_liens: bool | None
    judgments: bool | None
    bond_claims: bool | None
    credit_score_range: str | None
    has_prior_bonding: bool | None
    years_in_business: int | None
    has_financial_statements: bool | None
    working_capital: float | None


POSITIVE_WEIGHT = 10
NEGATIVE_WEIGHT = 15


def evaluate_lead(lead: ScorableLead) -> LeadScoreResult:
    positive_factors: list[str] = []
    negative_factors: list[str] = []

    if lead.interested_in_public_work is True:
        positive_factors.append('Contractor interested in public/government work')

    add_boolean_factor(lead.bankruptcies, 'No bankruptcies', 'Recent bankruptcy', positive_factors, negative_factors)
    add_boolean_factor(lead.foreclosures, 'No foreclosures', 'Foreclosure', positive_factors, negative_factors)
    add_boolean_factor(lead.tax_liens, 'No tax liens', 'Tax liens', positive_factors, negative_factors)
    add_boolean_factor(lead.judgments, 'No judgments', 'Judgments', positive_factors, negative_factors)
    add_boolean_factor(lead.bond_claims, 'No prior bond claims', 'Prior bond claims', positive_factors, negative_factors)

    credit_floor = parse_credit_score_floor(lead.credit_score_range)
    if credit_floor is not None:
        if credit_floor > 680:
            positive_factors.append('Credit score above 680')
        elif credit_floor < 620:
            negative_factors.append('Low credit score')

    if lead.has_prior_bonding is True:
        positive_factors.append('Prior bonding experience')

    if lead.years_in_business is not None:
        if lead.years_in_business >= 2:
            positive_factors.append('2+ years in business')
        elif lead.years_in_business < 2:
            negative_factors.append('Very new business')

    if lead.has_financial_statements is True:
        positive_factors.append('Has financial statements')
    elif lead.has_financial_statements is False:
        negative_factors.append('No financial documents')

    if lead.working_capital is not None:
        if lead.working_capital > 0:
            positive_factors.append('Positive working capital')
        elif lead.working_capital <= 0:
            negative_factors.append('Non-positive working capital')

    score = calculate_score(positive_factors, negative_factors)
    return LeadScoreResult(
        score=score,
        category=categorize_score(score, negative_factors),
        positive_factors=tuple(positive_factors),
        negative_factors=tuple(negative_factors),
    )


def add_boolean_factor(
    value: bool | None,
    positive_label: str,
    negative_label: str,
    positive_factors: list[str],
    negative_factors: list[str],
) -> None:
    if value is False:
        positive_factors.append(positive_label)
    elif value is True:
        negative_factors.append(negative_label)


def parse_credit_score_floor(credit_score_range: str | None) -> int | None:
    if not credit_score_range:
        return None
    numbers = [int(number) for number in findall(r'\d+', credit_score_range)]
    if not numbers:
        lowered = credit_score_range.casefold()
        if 'low' in lowered or 'poor' in lowered:
            return 0
        if 'excellent' in lowered or 'good' in lowered:
            return 700
        return None
    return min(numbers)


def calculate_score(positive_factors: list[str], negative_factors: list[str]) -> int:
    raw_score = 50 + (len(positive_factors) * POSITIVE_WEIGHT) - (len(negative_factors) * NEGATIVE_WEIGHT)
    score = max(0, min(100, raw_score))
    if negative_factors:
        return min(score, 79)
    return score


def categorize_score(score: int, negative_factors: list[str]) -> LeadReviewCategory:
    if score >= 80 and not negative_factors:
        return LeadReviewCategory.STRONG_CANDIDATE
    if score < 50 or len(negative_factors) >= 3:
        return LeadReviewCategory.HIGHER_RISK
    return LeadReviewCategory.NEEDS_REVIEW
