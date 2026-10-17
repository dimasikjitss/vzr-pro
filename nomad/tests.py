from decimal import Decimal
from datetime import date
from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User

from insurance.models import Branch, IndividualHolder, CompanyHolder, Profile
from nomad.models import NomadPolicy, NomadInsuredPerson, NomadTariff
from nomad.views import calculate_nomad_person


class NomadLogicTests(TestCase):
    def test_calculate_nomad_person_coefficients(self):
        ref_date = date(2026, 6, 1)
        sum_insured = Decimal('100000.00')
        rate = Decimal('0.46')

        # 1. Младенец (3 года) -> k=2.0
        dob_infant = date(2023, 1, 1)
        res_infant = calculate_nomad_person(sum_insured, rate, dob_infant, ref_date)
        self.assertEqual(res_infant['age'], 3)
        self.assertEqual(res_infant['age_coeff'], Decimal('2.0'))
        self.assertEqual(res_infant['netto'], Decimal('920.00'))
        self.assertEqual(res_infant['nsp'], Decimal('18.40'))
        self.assertEqual(res_infant['gross'], Decimal('938.40'))

        # 2. Ребенок (10 лет) -> k=1.8
        dob_child = date(2016, 1, 1)
        res_child = calculate_nomad_person(sum_insured, rate, dob_child, ref_date)
        self.assertEqual(res_child['age'], 10)
        self.assertEqual(res_child['age_coeff'], Decimal('1.8'))
        self.assertEqual(res_child['netto'], Decimal('828.00'))
        self.assertEqual(res_child['nsp'], Decimal('16.56'))
        self.assertEqual(res_child['gross'], Decimal('844.56'))

        # 3. Взрослый (30 лет) -> k=1.0
        dob_adult = date(1996, 1, 1)
        res_adult = calculate_nomad_person(sum_insured, rate, dob_adult, ref_date)
        self.assertEqual(res_adult['age'], 30)
        self.assertEqual(res_adult['age_coeff'], Decimal('1.0'))
        self.assertEqual(res_adult['netto'], Decimal('460.00'))
        self.assertEqual(res_adult['nsp'], Decimal('9.20'))
        self.assertEqual(res_adult['gross'], Decimal('469.20'))

    def test_individual_holder_sync(self):
        user = User.objects.create(username='agent_test_ind')
        branch = Branch.objects.create(name='Ошский филиал', code='02')
        ind = IndividualHolder.objects.create(
            name='СУЛАЙМАНОВ А.Б.',
            phone='+996777123456',
            inn='10101199012345',
            address='Г. ОШ, УЛ. ЛЕНИНА 1',
            passport='ID9876543',
            relative_contact='+996777654321'
        )
        policy = NomadPolicy.objects.create(
            agent=user,
            branch=branch,
            holder=ind,
            date_from=date(2026, 7, 1),
            date_to=date(2026, 7, 15),
        )
        self.assertEqual(policy.holder_name, 'СУЛАЙМАНОВ А.Б.')
        self.assertEqual(policy.holder_phone, '+996777123456')
        self.assertEqual(policy.holder_passport, 'ID9876543')
        self.assertEqual(policy.relative_contact, '+996777654321')
        self.assertEqual(policy.days_count, 15)
        self.assertTrue(policy.policy_number.startswith('VT02#'))

    def test_company_holder_sync(self):
        user = User.objects.create(username='agent_test_comp')
        branch = Branch.objects.create(name='Бишкек', code='01')
        comp = CompanyHolder.objects.create(
            company_name='ОСОО ТЯНЬ-ШАНЬ ТРЕВЕЛ',
            phone='+996312555555',
            inn='01234567891011',
            legal_address='Г. БИШКЕК, УЛ. БАЙТИК БААТЫРА 10',
            signatory_name='ТОКТОГУЛОВ Т.Т.'
        )
        policy = NomadPolicy.objects.create(
            agent=user,
            branch=branch,
            holder=comp,
            date_from=date(2026, 8, 1),
            date_to=date(2026, 8, 10),
        )
        self.assertEqual(policy.holder_name, 'ОСОО ТЯНЬ-ШАНЬ ТРЕВЕЛ')
        self.assertEqual(policy.holder_passport, 'ЮР. ЛИЦО')
        self.assertEqual(policy.relative_contact, 'ТОКТОГУЛОВ Т.Т.')
        self.assertEqual(policy.days_count, 10)

    def test_group_insured_persons_and_totals(self):
        user = User.objects.create(username='agent_test_grp')
        branch = Branch.objects.create(name='Бишкек', code='01')
        ind = IndividualHolder.objects.create(
            name='КАСЫМОВ К.К.',
            phone='+996555000111',
            address='БИШКЕК',
            passport='ID111222'
        )
        policy = NomadPolicy.objects.create(
            agent=user,
            branch=branch,
            holder=ind,
            date_from=date(2026, 9, 1),
            date_to=date(2026, 9, 10),
        )
        p1 = NomadInsuredPerson.objects.create(
            policy=policy,
            full_name='КАСЫМОВ К.К.',
            date_of_birth=date(1990, 5, 10),
            passport_number='ID111222',
            sum_insured=Decimal('100000.00'),
            premium_netto=Decimal('460.00')
        )
        p2 = NomadInsuredPerson.objects.create(
            policy=policy,
            full_name='КАСЫМОВ С.К.',
            date_of_birth=date(2023, 2, 1),
            passport_number='ID333444',
            sum_insured=Decimal('100000.00'),
            premium_netto=Decimal('920.00')
        )
        self.assertEqual(p1.nsp_amount, Decimal('9.20'))
        self.assertEqual(p1.premium_gross, Decimal('469.20'))
        self.assertEqual(p2.nsp_amount, Decimal('18.40'))
        self.assertEqual(p2.premium_gross, Decimal('938.40'))
        self.assertEqual(policy.insured_persons.count(), 2)


class NomadExtendedEdgeCaseTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username='nomad_agent_test', password='testpassword123')
        self.branch = Branch.objects.create(name='Центральный филиал', code='01')
        
        # Гарантированное создание/привязка профиля агента
        Profile.objects.update_or_create(
            user=self.user,
            defaults={'branch': self.branch}
        )

        NomadTariff.objects.create(
            program='BRONZE',
            days_min=1,
            days_max=30,
            percent_rate=Decimal('0.46')
        )

    def test_age_edge_exact_5_years(self):
        ref_date = date(2026, 6, 15)
        dob = date(2021, 6, 16)
        res = calculate_nomad_person(Decimal('100000.00'), Decimal('0.46'), dob, ref_date)
        self.assertEqual(res['age'], 4)
        self.assertEqual(res['age_coeff'], Decimal('2.0'))

    def test_age_edge_exact_6_years_transition(self):
        ref_date = date(2026, 6, 15)
        dob = date(2020, 6, 15)
        res = calculate_nomad_person(Decimal('100000.00'), Decimal('0.46'), dob, ref_date)
        self.assertEqual(res['age'], 6)
        self.assertEqual(res['age_coeff'], Decimal('1.8'))

    def test_age_edge_exact_14_years_adult_transition(self):
        ref_date = date(2026, 6, 15)
        dob = date(2012, 6, 15)
        res = calculate_nomad_person(Decimal('100000.00'), Decimal('0.46'), dob, ref_date)
        self.assertEqual(res['age'], 14)
        self.assertEqual(res['age_coeff'], Decimal('1.0'))
        self.assertEqual(res['gross'], Decimal('469.20'))

    def test_leap_year_birthday_calculation(self):
        ref_date = date(2026, 3, 1)
        dob = date(2020, 2, 29)
        res = calculate_nomad_person(Decimal('100000.00'), Decimal('0.46'), dob, ref_date)
        self.assertEqual(res['age'], 6)
        self.assertEqual(res['age_coeff'], Decimal('1.8'))

    def test_single_day_policy_duration(self):
        ind = IndividualHolder.objects.create(name='ТЕСТОВ Т.Т.', phone='+996', passport='ID1')
        policy = NomadPolicy.objects.create(
            agent=self.user,
            branch=self.branch,
            holder=ind,
            date_from=date(2026, 9, 10),
            date_to=date(2026, 9, 10),
        )
        self.assertEqual(policy.days_count, 1)

    def test_insured_person_custom_citizenship_storage(self):
        ind = IndividualHolder.objects.create(name='ГИД АСАНОВ', phone='+996', passport='ID2')
        policy = NomadPolicy.objects.create(agent=self.user, branch=self.branch, holder=ind, date_from=date(2026, 9, 1), date_to=date(2026, 9, 5))
        
        tourist_de = NomadInsuredPerson.objects.create(
            policy=policy,
            full_name='HANS MULLER',
            date_of_birth=date(1985, 4, 12),
            passport_number='C1234567',
            citizenship='ГЕРМАНИЯ',
            sum_insured=Decimal('100000'),
            premium_netto=Decimal('460')
        )
        self.assertEqual(tourist_de.citizenship, 'ГЕРМАНИЯ')

    def test_default_beneficiary_fallback(self):
        ind = IndividualHolder.objects.create(name='ИВАНОВ И.И.', phone='+996', passport='ID3')
        # Если бенефициар не передан (None), модель подставляет дефолт
        policy = NomadPolicy.objects.create(
            agent=self.user,
            branch=self.branch,
            holder=ind,
            date_from=date(2026, 9, 1),
            date_to=date(2026, 9, 5),
        )
        self.assertIn('ЗАСТРАХОВАННЫЙ', policy.beneficiary.upper())

    def test_custom_beneficiary_assignment(self):
        ind = IndividualHolder.objects.create(name='ИВАНОВ И.И.', phone='+996', passport='ID4')
        policy = NomadPolicy.objects.create(
            agent=self.user,
            branch=self.branch,
            holder=ind,
            date_from=date(2026, 9, 1),
            date_to=date(2026, 9, 5),
            beneficiary='ПЕТРОВ ПЕТР ПЕТРОВИЧ'
        )
        self.assertEqual(policy.beneficiary, 'ПЕТРОВ ПЕТР ПЕТРОВИЧ')

    def test_mixed_citizenship_group_aggregation(self):
        comp = CompanyHolder.objects.create(company_name='TOUR KG', phone='+996', signatory_name='ДИРЕКТОР')
        policy = NomadPolicy.objects.create(agent=self.user, branch=self.branch, holder=comp, date_from=date(2026, 9, 1), date_to=date(2026, 9, 5))
        
        NomadInsuredPerson.objects.create(policy=policy, full_name='T1', date_of_birth=date(1990, 1, 1), passport_number='P1', citizenship='ФРАНЦИЯ', sum_insured=Decimal('100000'), premium_netto=Decimal('460'))
        NomadInsuredPerson.objects.create(policy=policy, full_name='T2', date_of_birth=date(1995, 1, 1), passport_number='P2', citizenship='КИТАЙ', sum_insured=Decimal('100000'), premium_netto=Decimal('460'))
        NomadInsuredPerson.objects.create(policy=policy, full_name='T3', date_of_birth=date(2023, 1, 1), passport_number='P3', citizenship='РОССИЯ', sum_insured=Decimal('100000'), premium_netto=Decimal('920'))

        self.assertEqual(policy.insured_persons.count(), 3)
        citizenships = list(policy.insured_persons.values_list('citizenship', flat=True))
        self.assertListEqual(citizenships, ['ФРАНЦИЯ', 'КИТАЙ', 'РОССИЯ'])

    def test_precision_nsp_rounding(self):
        ind = IndividualHolder.objects.create(name='ТЕСТ', phone='+996', passport='ID5')
        policy = NomadPolicy.objects.create(agent=self.user, branch=self.branch, holder=ind, date_from=date(2026, 9, 1), date_to=date(2026, 9, 2))
        
        person = NomadInsuredPerson.objects.create(
            policy=policy,
            full_name='ROUND TEST',
            date_of_birth=date(1990, 1, 1),
            passport_number='R1',
            sum_insured=Decimal('50000'),
            premium_netto=Decimal('333.33')
        )
        self.assertEqual(person.nsp_amount, Decimal('6.67'))
        self.assertEqual(person.premium_gross, Decimal('340.00'))

    def test_nomad_create_view_company_post(self):
        self.client.force_login(self.user)
        payload = {
            'holder_kind': 'company',
            'company_name': 'ООО ЕВРАЗИЯ ТРЕВЕЛ',
            'company_inn': '01234567890123',
            'company_okpo': '98765432',
            'company_address': 'БИШКЕК',
            'company_phone': '+996555111222',
            'company_signatory': 'АЛИЕВ А.А.',
            'company_citizenship_type': 'Другое',
            'company_citizenship_manual': 'КАЗАХСТАН',
            'beneficiary_company': 'АЛИЕВ А.А.',
            'start_date': '2026-09-15',
            'end_date': '2026-09-20',
            'sum_insured': '100000',
            'insured_name[]': ['JOHN DOE', 'JANE DOE'],
            'insured_citizenship[]': ['США', 'КАНАДА'],
            'insured_dob[]': ['1992-05-10', '1994-08-20'],
            'insured_passport[]': ['US111', 'CA222'],
        }
        response = self.client.post(reverse('nomad:create_policy_nomad'), payload)
        self.assertEqual(response.status_code, 302)

        created_policy = NomadPolicy.objects.filter(holder_name='ООО ЕВРАЗИЯ ТРЕВЕЛ').first()
        self.assertIsNotNone(created_policy)
        self.assertEqual(created_policy.citizenship, 'КАЗАХСТАН')
        self.assertEqual(created_policy.beneficiary, 'АЛИЕВ А.А.')
        self.assertEqual(created_policy.insured_persons.count(), 2)

    def test_nomad_preview_view_no_db_persistence(self):
        self.client.force_login(self.user)
        payload = {
            'holder_kind': 'individual',
            'holder_name': 'ЧЕРНОВИКОВ Ч.Ч.',
            'holder_passport': 'ID000999',
            'holder_phone': '+996555999000',
            'holder_address': 'ОШ',
            'holder_relative': '+996555999001',
            'start_date': '2026-10-01',
            'end_date': '2026-10-05',
            'sum_insured': '100000',
            'insured_name[]': ['TOURIST ONE'],
            'insured_citizenship[]': ['ИТАЛИЯ'],
            'insured_dob[]': ['1998-03-15'],
            'insured_passport[]': ['IT555'],
        }
        initial_count = NomadPolicy.objects.count()
        response = self.client.post(reverse('nomad:nomad_preview'), payload)
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'ПРОЕКТ / DRAFT')
        self.assertContains(response, 'TOURIST ONE')
        self.assertEqual(NomadPolicy.objects.count(), initial_count)