from backend.scripts.seed_leads import SAMPLE_LEADS, seed_sample_leads


def test_sample_seed_payloads_have_expected_shape():
    assert len(SAMPLE_LEADS) == 2
    emails = {lead['email'] for lead in SAMPLE_LEADS}
    assert emails == {'jordan.principal@example.com', 'casey.contractor@example.com'}

    for lead in SAMPLE_LEADS:
        assert lead['full_name']
        assert lead['phone_number']
        assert lead['email']
        assert lead['bond_type_needed']
        assert lead['notes']


def test_seed_sample_leads_creates_two_idempotent_records(db_session):
    first_seed = seed_sample_leads(db_session)
    second_seed = seed_sample_leads(db_session)

    assert len(first_seed) == 2
    assert len(second_seed) == 2
    assert [lead.id for lead in second_seed] == [lead.id for lead in first_seed]
    assert all(lead.id is not None for lead in first_seed)
    assert {lead.lead_status for lead in first_seed} <= {
        'Strong Candidate',
        'Needs Review',
        'Higher Risk / Human Review Required',
    }
