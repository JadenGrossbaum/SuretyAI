VALID_LEAD = {
    'full_name': 'Jordan Principal',
    'company_name': 'Principal Builders LLC',
    'phone_number': '+15555550123',
    'email': 'JORDAN@EXAMPLE.COM',
    'contractor_type': 'general contractor',
    'interested_in_public_work': True,
    'bond_type_needed': 'performance and payment bond',
    'estimated_contract_amount': 250000.0,
    'has_prior_bonding': True,
    'current_bonding_capacity': 500000.0,
    'credit_score_range': '700-749',
    'bankruptcies': False,
    'foreclosures': False,
    'tax_liens': False,
    'judgments': False,
    'bond_claims': False,
    'spouse_financial_issues': False,
    'years_in_business': 6,
    'annual_revenue': 1250000.0,
    'working_capital': 150000.0,
    'has_financial_statements': True,
    'preferred_callback_time': 'weekday mornings',
    'notes': 'Interested in bidding public jobs this quarter.',
}


def test_create_lead(client):
    response = client.post('/api/leads', json=VALID_LEAD)

    assert response.status_code == 201
    data = response.json()
    assert data['id'] == 1
    assert data['email'] == 'jordan@example.com'
    assert data['lead_score'] == 100
    assert data['lead_status'] == 'Strong Candidate'
    assert data['created_at']


def test_list_leads(client):
    first = dict(VALID_LEAD, email='first@example.com')
    second = dict(VALID_LEAD, full_name='Second Principal', email='second@example.com')
    client.post('/api/leads', json=first)
    client.post('/api/leads', json=second)

    response = client.get('/api/leads')

    assert response.status_code == 200
    leads = response.json()
    assert len(leads) == 2
    assert {lead['email'] for lead in leads} == {'first@example.com', 'second@example.com'}


def test_get_lead_by_id(client):
    created = client.post('/api/leads', json=VALID_LEAD).json()

    response = client.get('/api/leads/{}'.format(created['id']))

    assert response.status_code == 200
    assert response.json()['full_name'] == VALID_LEAD['full_name']


def test_get_missing_lead_returns_404(client):
    response = client.get('/api/leads/999')

    assert response.status_code == 404
    assert response.json()['detail'] == 'Lead not found'


def test_create_lead_validates_email(client):
    payload = dict(VALID_LEAD, email='not-an-email')

    response = client.post('/api/leads', json=payload)

    assert response.status_code == 422


def test_create_lead_rejects_negative_contract_amount(client):
    payload = dict(VALID_LEAD, estimated_contract_amount=-1)

    response = client.post('/api/leads', json=payload)

    assert response.status_code == 422
