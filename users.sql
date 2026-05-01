--
-- PostgreSQL database dump
--

\restrict 1WIqvDlMpzCpfNPUwC2AvynDLuOOduMzPHO4pB0i3u7FUgkoy91zqWGz7tx74xD

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
-- Data for Name: auth_user; Type: TABLE DATA; Schema: public; Owner: insurance_user
--

INSERT INTO public.auth_user (id, password, last_login, is_superuser, username, first_name, last_name, email, is_staff, is_active, date_joined) VALUES (2, 'pbkdf2_sha256$390000$eMyFcJubOrnjMK9wDuKHZA$scbz7WnE9VI10mxCL2/QZnZc37gxrN5QA20aL8IWZIU=', '2026-03-16 11:08:06.428412+00', false, 'Katysheva', 'Алия', 'Катышева', 'bishkek@gso.kg', false, true, '2026-03-16 11:04:16+00');
INSERT INTO public.auth_user (id, password, last_login, is_superuser, username, first_name, last_name, email, is_staff, is_active, date_joined) VALUES (1, 'pbkdf2_sha256$390000$aRtYtsorg4mjx8JWFNeLQV$jrG4JxXQHMAZ2c/COLVbm9wDydsgRvUZJ+0tb9aUOxg=', '2026-03-16 11:48:34.60079+00', true, 'Malika', 'Malika', 'Bootaeva', 'malika@gmail.com', true, true, '2026-03-15 17:45:45+00');


--
-- Name: auth_user_id_seq; Type: SEQUENCE SET; Schema: public; Owner: insurance_user
--

SELECT pg_catalog.setval('public.auth_user_id_seq', 2, true);


--
-- PostgreSQL database dump complete
--

\unrestrict 1WIqvDlMpzCpfNPUwC2AvynDLuOOduMzPHO4pB0i3u7FUgkoy91zqWGz7tx74xD

