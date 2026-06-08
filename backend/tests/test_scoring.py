from types import SimpleNamespace

from app.scoring import LeadReviewCategory, evaluate_lead


def make_lead(**overrides):
    defaults = {
        'interested_in_public_work': True,
        'bankruptcies': False,
        'foreclosures': False,
        'tax_liens': False,
        'judgments': False,
        'bond_claims': False,
        'credit_score_range': '720-759',
        'has_prior_bonding': True,
        'years_in_business': 5,
        'has_financial_statements': True,
        'working_capital': 100000.0,
    }
    defaults.update(overrides)
    return SimpleNamespace(**defaults)


def test_strong_candidate_scoring_category():
    result = evaluate_lead(make_lead())

    assert result.category == LeadReviewCategory.STRONG_CANDIDATE
    assert result.score == 100
    assert 'Credit score above 680' in result.positive_factors
    assert result.negative_factors == ()


def test_needs_review_scoring_category():
    result = evaluate_lead(
        make_lead(
            interested_in_public_work=False,
            credit_score_range='650-679',
            has_prior_bonding=False,
            tax_liens=True,
            years_in_business=2,
        )
    )

    assert result.category == LeadReviewCategory.NEEDS_REVIEW
    assert 50 <= result.score < 80


def test_higher_risk_scoring_category_for_multiple_negative_factors():
    result = evaluate_lead(
        make_lead(
            bankruptcies=True,
            foreclosures=True,
            tax_liens=True,
            judgments=True,
            bond_claims=True,
            credit_score_range='580-619',
            has_financial_statements=False,
            years_in_business=0,
            working_capital=-5000.0,
        )
    )

    assert result.category == LeadReviewCategory.HIGHER_RISK
    assert result.score < 50
    assert 'Recent bankruptcy' in result.negative_factors
    assert 'Low credit score' in result.negative_factors


def test_scoring_categories_do_not_use_approval_or_denial_language():
    forbidden_terms = ('approve', 'approved', 'deny', 'denied')

    for category in LeadReviewCategory:
        normalized = category.value.casefold()
        assert all(term not in normalized for term in forbidden_terms)
