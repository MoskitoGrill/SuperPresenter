# Výskyty složených constructů v songs

Inventář všech XML elementů repetition (včetně opakování uvnitř variant).
Víceřádkový text je spojen mezerou stejně jako při importu aplikace.

Kontrola 6. 9. 2026: 858 souborů, 860 výrazů, 853 přijatých při sjednocení sekcí všech variant.

| Soubor | Opakování | Výraz | Konstrukce |
|---|---|---|---|
| `songs/_.xml` | `default` | `v1 r1 v2 r1 v3 (r1)` | `group` |
| `songs/alabastr_(suchdol_version).xml` | `default` | `v1 (r1) v2 v3` | `group` |
| `songs/at_pozehnan_je_buh.xml` | `default` | `v1 v2 r0 (r1) v3 v4 (r1) (b1)*4 (r1)` | `group, multiply` |
| `songs/at_srdce_me_tebe_vida.xml` | `default` | `v1 r1 (b1.1)*3 b1.2` | `group, multiply, line` |
| `songs/bud_vladcem_mym.xml` | `default` | `v1 r1 v2 (r1)` | `group` |
| `songs/budu_jen_o_tve_lasce_zpivat.xml` | `default` | `v1 (r1) v1 (r1)` | `group` |
| `songs/dekuji.xml` | `default` | `v1 (r1) (r2) v2 (r3) (r4)` | `group` |
| `songs/do_tmy_na_svet.xml` | `default` | `v1 r1 v2 r1 (b1)*4 (r1)` | `group, multiply` |
| `songs/do_tmy_na_svet.xml` | `Ivo` | `v1 r1 v2 r1 (b1)*3 r1` | `group, multiply` |
| `songs/dobrorec_duse_ma_hospodinu.xml` | `default` | `(v1 v2) v2 v1` | `group` |
| `songs/domov.xml` | `default` | `v1 r1 r2 v1 (r1 r2)` | `group` |
| `songs/duchu_svaty_jsi_tu_vitany_(suchdol_version).xml` | `default` | `v1 v2 v2.3 r1 v1 v2 v2.3 r1 b1.1 b1.2*4 (r1)` | `group, multiply, line` |
| `songs/hla_stojim_pri_dverach.xml` | `default` | `v1 r1 v2 r1 (v3) r1` | `group` |
| `songs/hledam_tvoji_tvar.xml` | `default` | `v1 (r1) b1` | `group` |
| `songs/hoden_je_beranek.xml` | `JancaDada` | `v1 r1 v1 r1.1:2 r1 v1` | `line, range` |
| `songs/jedine_miesto.xml` | `Mira-band` | `(v1 v2 v3)` | `group` |
| `songs/jesua-meho_srdce_kral.xml` | `default` | `(v1)*4 (r1)*2 (v1)*4 (r1)*4 (v2)*4 (r1)*2` | `group, multiply` |
| `songs/jmeno_slavime_tve_-_hosana.xml` | `default` | `(v1) r1 (v2) r1` | `group` |
| `songs/jsi_slavy kral.xml` | `` | `(v1)*3 v2 (r1) (v1)*3 v2 (r1)` | `group, multiply` |
| `songs/kral_kralu__ua__.xml` | `default` | `v1 r1 v2 r1 v3 v4 (r1)` | `group` |
| `songs/muj_krali_ma_spaso.xml` | `default` | `(v1 v2 r1 r2)` | `group` |
| `songs/muj_pan.xml` | `default` | `(v1 r1) v2 r1` | `group` |
| `songs/muj_svet.xml` | `default` | `v1 r1 b2 v2 r1 b2 (b1) r1 b2 r1.9 b2` | `group, line` |
| `songs/my_jeho_deti__ua__.xml` | `default` | `v1 (r1) v2 (r1)*3` | `group, multiply` |
| `songs/na_nebesich_je_tvuj_trun.xml` | `default` | `v1 (r1) v1` | `group` |
| `songs/na_slave_sve_jsi_netrval.xml` | `default` | `v1 r1 v1 (r1)` | `group` |
| `songs/naveky_svaty_opravit.xml` | `default` | `v1 b1 r1 v2 (r1) (b1) (r1)` | `group` |
| `songs/nyni_se_radost_stala__ua__.xml` | `default` | `(v1) (v2) (v3) (v4) (v5)` | `group` |
| `songs/o_prijd_o_prijd_imanuel.xml` | `Mira-band` | `(v1 v2 v3)` | `group` |
| `songs/o_v_betleme_je_radostna_zprava__ua___.xml` | `default` | `(v1) (v2) (v3) (v4) (v5) (v6)` | `group` |
| `songs/oslav_ho_nebe.xml` | `Mira-band` | `(v1 v2 r) r` | `group` |
| `songs/pana_chval_duse_ma.xml` | `default` | `r1 v1 r1 v2 r1 v3 (r1)` | `group` |
| `songs/pane_mne_chybeji_slova.xml` | `default` | `v1 (r1) v2 (r1) v3 (r1)` | `group` |
| `songs/pane_smadni_sme_po_tebe.xml` | `default` | `(r1)*4 (v1) (v2)` | `group, multiply` |
| `songs/pane_vzdy_ked_tvoju_svatost_zriem.xml` | `default` | `v1 v2 (r1)` | `group` |
| `songs/pokus.xml` | `pokus` | `v1 (r1) v2` | `group` |
| `songs/pred_tebou_smim_pokleknout.xml` | `default` | `v1 (r1) v2 (r1)` | `group` |
| `songs/radost_zeme__ua__.xml` | `default` | `v1 v2 v3 (v2)` | `group` |
| `songs/reka_tve_lasky.xml` | `default` | `v1 (r1)` | `group` |
| `songs/shma_yisrael.xml` | `default` | `(v1) (r1) (b1)` | `group` |
| `songs/slav__uk__.xml` | `default` | `v1 r1 v2 r1 r2 (b1) v3` | `group` |
| `songs/Slnko a mesiac.xml` | `default` | `(v1 v2 v3) (b1)*3 v3` | `group, multiply` |
| `songs/svate_jmeno_mas-immanuel.xml` | `default` | `v1 (r1)` | `group` |
| `songs/svaty_naveky__ua.xml` | `default` | `v1 r1 r2 v2 r3 r4 (r1) r3 r4` | `group` |
| `songs/tilo_lomine.xml` | `default` | `v1 r1 v2 r1 v3 (r1)` | `group` |
| `songs/tohle_je_laska_tva_(suchdol_version).xml` | `default` | `v1 r1 v2 (b1)` | `group` |
| `songs/ty_jsi.xml` | `default` | `v1 r1 v1 r2 b1 v2 b1.1:3 b1` | `line, range` |
| `songs/ty_jsi_jediny_buh.xml` | `default` | `(v1) r1 v1 r1` | `group` |
| `songs/ty_jsi_mocny_ty_jsi_svaty.xml` | `default` | `(v1) (r1)*4 (v1) (r1)*4` | `group, multiply` |
| `songs/ty_jsi miloval_spravedlnost.xml` | `default` | `(v1) (r1) (v2) (r2)` | `group` |
| `songs/uk_-_krev_svateho_byla_usmirena.xml` | `default` | `v1 r1 v2 r1 r1 r1.3:4 v3 r2 r2 r2.3:4` | `line, range` |
| `songs/uz_vidim_krale_slavy.xml` | `default` | `v1 (r1) v2 (r1) v3 (r1)` | `group` |
| `songs/uzasny_nadherny_krali.xml` | `default` | `v1 r1 v2 r1 v3 (r1)` | `group` |
| `songs/ved_me_stale_bliz.xml` | `default` | `(v1 v2 r1)` | `group` |
| `songs/viem_ze_moj_pan_zivy_je.xml` | `default` | `(r1) v1 (r1) v2 (r1) v3 (r1)` | `group` |
| `songs/viem_ze_môj_pan_zivy_je.xml` | `default` | `(r1) v1 (r1) v2 (r1) v3 (r1)` | `group` |
| `songs/vyvyseny_svoj_tron_si_v_slave_mal.xml` | `default` | `v1 (b1) r1 (v2) (b1) r1 (b2)*3 r1` | `group, multiply` |
| `songs/vyvysuji_tebe_pane.xml` | `JancaDada` | `v1 (r1) v1 (r1) v1.1` | `group, line` |
| `songs/vzdavame_ti_chvalu.xml` | `default` | `(v1) v2 v3 (v1) (v2 v3)` | `group` |
| `songs/vzyvam_a_slavim_tve_jmeno.xml` | `default` | `(v1) (v2)` | `group` |
| `songs/vzyvam_jmeno_jezis.xml` | `default` | `((v1) (r1)) (v1)` | `group, nested` |
| `songs/znovu_-_premyslim_nad_obeti.xml` | `default` | `v1 r1 v2 r1 b1 (r1)` | `group` |
| `songs/ЕМАНУЇЛ.xml` | `default` | `v1 r1 v2 (r1) v3 (r1)` | `group` |

## Odmítnuté výrazy

| Soubor | Opakování | Výraz | Chyba |
|---|---|---|---|
| `songs/buh_vsech_narodu.xml` | `default` | `v1 r1 v2 b` | `Neznámá sekce "b" (pozice 9, počítáno od 0)` |
| `songs/buh_vsech_narodu.xml` | `default` | `v1 r1 v2 b` | `Neznámá sekce "b" (pozice 9, počítáno od 0)` |
| `songs/duchu_svaty_jsi_tu_vitany_(suchdol_version).xml` | `default` | `v1 v2 v2.3 r1 v1 v2 v2.3 r1 b1.1 b1.2*4 (r1)` | `Neznámá sekce "*4" (pozice 37, počítáno od 0)` |
| `songs/jak_vzacna_milost_otcova.xml` | `default` | `V1 V2 V3` | `Neznámá sekce "V1" (pozice 0, počítáno od 0)` |
| `songs/je_jeden_hlas_co_mel_by_znit.xml` | `JančaDada` | `v1 v2 r1 v1 v2 r1 r1` | `Neznámá sekce "r1" (pozice 6, počítáno od 0)` |
| `songs/Kancionálky/110 - Pán Jeºíτ p²ijde zas.xml` | `default` | `v1 r1 v2 r1 v3 r1 v4 r1` | `Neznámá sekce "v4" (pozice 18, počítáno od 0)` |
| `songs/moc_cest_a_slava.xml` | `default` | `v1 r1 v2 r1` | `Neznámá sekce "r1" (pozice 3, počítáno od 0)` |
