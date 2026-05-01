--
-- PostgreSQL database dump
--

\restrict emgmdPgXG5OugXQDiq3h5bbI7uz3mspgLgsUPbAnP8THeFKBjAReanUeUnTb51U

-- Dumped from database version 16.13 (Ubuntu 16.13-0ubuntu0.24.04.1)
-- Dumped by pg_dump version 16.13 (Ubuntu 16.13-0ubuntu0.24.04.1)

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

--
-- Data for Name: insurance_insurancepolicy; Type: TABLE DATA; Schema: public; Owner: insurance_user
--

INSERT INTO public.insurance_insurancepolicy (id, policy_number, issue_date, holder_name, date_from, date_to, days_count, territory, program, exchange_rate, activity_type, agent_id, branch_id, currency_code, holder_address, holder_passport, holder_phone, relative_contact, total_premium_currency, total_premium_som, holder_inn) VALUES (1, 'VZR00#000001', '2026-03-16', 'ELDIIAR KALDARBEKOV', '2026-04-01', '2026-04-05', 5, 'ASIA', 'SILVER', 87.4500, 'A+', 1, 1, 'USD', 'Г.Бишкек', 'PE0559533', '+996707545400', '+996707545400', 5.81, 508.08, '22306198900613');
INSERT INTO public.insurance_insurancepolicy (id, policy_number, issue_date, holder_name, date_from, date_to, days_count, territory, program, exchange_rate, activity_type, agent_id, branch_id, currency_code, holder_address, holder_passport, holder_phone, relative_contact, total_premium_currency, total_premium_som, holder_inn) VALUES (3, 'VZR01#000001', '2026-03-16', 'MAZHIKEEVA GULCHAKHRA', '2026-03-19', '2026-04-02', 15, 'ASIA', 'SILVER', 87.4500, 'A+', 2, 2, 'USD', 'Bishkek', 'PE0055874', '+996708705560', '+996708705560', 41.72, 3648.41, '11107195200331');


--
-- Name: insurance_insurancepolicy_id_seq; Type: SEQUENCE SET; Schema: public; Owner: insurance_user
--

SELECT pg_catalog.setval('public.insurance_insurancepolicy_id_seq', 5, true);


--
-- PostgreSQL database dump complete
--

\unrestrict emgmdPgXG5OugXQDiq3h5bbI7uz3mspgLgsUPbAnP8THeFKBjAReanUeUnTb51U

