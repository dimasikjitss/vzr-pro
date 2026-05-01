--
-- PostgreSQL database dump
--

\restrict SPgU2of3BhjHbttdgvaSDah4RSeLMdo1ajy8vn9BMc4aH49Bw5koGnd0BATh6Ma

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
-- Data for Name: insurance_policycounter; Type: TABLE DATA; Schema: public; Owner: insurance_user
--

INSERT INTO public.insurance_policycounter (id, current_id, branch_code) VALUES (3, 2, '01');
INSERT INTO public.insurance_policycounter (id, current_id, branch_code) VALUES (1, 2, '00');


--
-- Name: insurance_policycounter_id_seq; Type: SEQUENCE SET; Schema: public; Owner: insurance_user
--

SELECT pg_catalog.setval('public.insurance_policycounter_id_seq', 3, true);


--
-- PostgreSQL database dump complete
--

\unrestrict SPgU2of3BhjHbttdgvaSDah4RSeLMdo1ajy8vn9BMc4aH49Bw5koGnd0BATh6Ma

