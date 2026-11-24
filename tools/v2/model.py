"""
Single source model for the structured (v2) version of the municipal
sanitary-establishment license process.

Every task in the original diagram (diagrams/license-process-bpmn.jpg)
is listed in ORIGINAL and referenced by exactly one v2 node through its
`orig` field, so nothing can be dropped silently: build.py fails if an
original step is unmapped or mapped twice.

Node types
  start, start_msg, end, end_error, end_escalation, timer,
  user, send, call, gw_x, gw_p, boundary_error, boundary_escalation
"""

# ---------------------------------------------------------------------------
# Original steps (Turkish labels as drawn; internal system names masked)
# ---------------------------------------------------------------------------
ORIGINAL = {
    "O1":  ("Ruhsat Müdürlüğü - Sıhhi Müessese Ruhsat Başvurusu İçin Evrak Kayıt, Kontrol ve Borç Bilgisi Sorgulama, Başvuru Beyan Formu Alma", "Ruhsat ve Denetim Müdürlüğü"),
    "O2":  ("Taşınmaz Birimi - Saha Denetimi Başlatma, Tahakkuk", "Taşınmaz Birimi (ekip saha tespitine yönlendirilir)"),
    "O3":  ("Taşınmaz Birimi - Saha Tespiti Onay", "Taşınmaz Birimi (tespit sonrası)"),
    "O4":  ("Başvuru Bilgi E-Postası, Tahakkuk Daveti", "otomatik (script task)"),
    "O5":  ("Taşınmaz Birimi - Tahakkuk Adımı", "Taşınmaz Birimi"),
    "O6":  ("[kurum içi proje adı] - Tahsilat", "Vezne"),
    "O7":  ("Yazı İşleri - Sıhhi Müessese Ruhsat Başvurusu Alma", "Yazı İşleri"),
    "O8":  ("Ruhsat Müdürlüğü - Taşınmaz Birimi Saha Tespiti ve Ruhsat Büro Personeli İşlemlerini Kontrolü", "Ruhsat ve Denetim Müdürü"),
    "O9":  ("Sıhhi Müessese Ruhsat Başvurusu - İtfaiye Raporu Talebi", "(rol belirtilmemiş)"),
    "O10": ("Kent Bilgi Servisi - Güncel Adres Tespiti", "Kent Bilgi Servisi / İmar Müd. Personeli"),
    "O11": ("İmar Müdürü - Adres Tespiti Onay", "İmar Müdürü"),
    "O12": ("Başkan Yardımcısı - Adres Tespiti Onay", "Başkan Yardımcısı"),
    "O13": ("Sıhhi Müessese Ruhsat Başvurusu - İmar Durumu Sorgulama", "İmar ve Şehircilik Müdürü"),
    "O14": ("Yapı Denetim Şefi (sol kol, ilk adım)", "Yapı Denetim Şefi"),
    "O15": ("Raportör (sol kol)", "Raportör"),
    "O16": ("Yapı Denetim Şefi (sol kol, kontrol)", "Yapı Denetim Şefi"),
    "O17": ("İmar ve Şehircilik Müd. (sol kol)", "İmar ve Şehircilik Müdürü"),
    "O18": ("Harita Şefi (sağ kol, ilk adım)", "Harita Şefi"),
    "O19": ("Raportör (sağ kol)", "Raportör"),
    "O20": ("Yapı Denetim Şefi (sağ kol, kontrol)", "Yapı Denetim Şefi"),
    "O21": ("İmar ve Şehircilik Müd. (sağ kol)", "İmar ve Şehircilik Müdürü"),
    "O22": ("Başkan Yardımcısı (imar görüşleri)", "Başkan Yardımcısı"),
    "O23": ("Ruhsat ve Denetim Müdürlüğü - Saha Denetimini Başlatma", "Ruhsat ve Denetim Müdürü"),
    "O24": ("İmar Durumuna Göre Başvuru İptal Bilgilendirmesi", "otomatik (script task)"),
    "O25": ("Ruhsat ve Denetim Müdürlüğü - Saha Denetimi", "Ruhsat ve Denetim Müdürlüğü"),
    "O26": ("Ruhsat ve Denetim Müdürlüğü - 2. Saha Denetimini Başlatma", "Ruhsat ve Denetim Müdürü"),
    "O27": ("Ruhsat ve Denetim Müdürlüğü 2. Saha Denetimi", "Ruhsat ve Denetim Müdürlüğü Saha Denetim Ekibi"),
    "O28": ("2. Denetim Sonrası Başvurunun İptali", "Ruhsat ve Denetim Müdürü"),
    "O29": ("Başvuru İptal Bilgilendirmesi", "otomatik (script task)"),
    "O30": ("Ruhsat ve Denetim Müdürlüğü - Komisyon Değerlendirme", "Ruhsat ve Denetim Müdürlüğü"),
    "O31": ("Bilgi E-Postası, Tahakkuk Davet", "otomatik (script task)"),
    "O32": ("Sıhhi Müessese Ruhsat Başvurusu - Tahakkuk Oluşturma İşlemi", "Tahakkuk personeli"),
    "O33": ("Sıhhi Müessese Ruhsat Başvurusu Tahsilat İşlemi", "Vezne"),
    "O34": ("Sıhhi Müessese Ruhsat Başvurusu Onay İşlemi", "Ruhsat ve Denetim Müdürü"),
    "O35": ("Başkan Yardımcısı - Sıhhi Müessese Ruhsat Onayı", "Ruhsat ve Denetim Müdürlüğü'nden sorumlu Başkan Yardımcısı"),
    "O36": ("Sıhhi Müessese Ruhsat Başvurusu'nun İptalinin Bilgilendirmesi", "Ruhsat ve Denetim Müdürlüğü"),
    "O37": ("Sıhhi Müessese Ruhsat Başvurusu'nun İptali İçin Bilgilendirme İşlemi", "Belediye Başkanı"),
    "O38": ("[kurum içi e-posta servisi] Mail Task", "otomatik (script task)"),
    "O39": ("Sıhhi Müessese Ruhsat Başvurusu Onayı", "Belediye Başkanı"),
    "O40": ("Sıhhi Müessese Ruhsat Başvurusu İptal Bilgilendirmesi", "Ruhsat ve Denetim Müdürü"),
    "O41": ("Ruhsatlandırma ve Vatandaşın Bilgilendirmesi", "Raportör"),
    "O42": ("Ruhsat Onay Bilgilendirmesi", "otomatik (script task)"),
    "T1":  ("Zamanlayıcı 15 Gün", "zamanlayıcı olay"),
}

# Errors thrown by stage end events and caught on Level 0
ERRORS = {
    "Err_Zoning":   ("Cancelled: zoning status", "ZONING_REJECTED"),
    "Err_Second":   ("Cancelled: after second inspection", "SECOND_INSPECTION_FAILED"),
    "Err_Deputy":   ("Cancelled: deputy mayor level", "CANCELLED_DEPUTY"),
    "Err_Mayor":    ("Cancelled: mayor level", "CANCELLED_MAYOR"),
    "Err_Commission": ("Rejected by commission", "COMMISSION_REJECTED"),
}
ESCALATIONS = {
    "Esc_Accrual": ("Debt due: transfer to collection (accrual)", "DEBT_DUE_ACCRUAL"),
    "Esc_Payment": ("Debt due: transfer to collection (payment)", "DEBT_DUE_PAYMENT"),
}

LANES = {
    "LD":   "Licensing & Inspection Directorate",
    "INSP": "Field Inspection Team",
    "REC":  "Records Office",
    "RE":   "Real Estate Unit",
    "CASH": "Cashier",
    "ACC":  "Accrual Staff",
    "GIS":  "City Information Service",
    "ZDIR": "Zoning & Urban Planning Director",
    "DEP":  "Deputy Mayor",
    "MAY":  "Mayor",
    "RAP":  "Rapporteur",
    "SYS":  "Automated Notifications",
    "ZAB":  "Municipal Police (Zabıta)",
}


def N(id, type, name, lane=None, col=0, row=0, **kw):
    d = dict(id=id, type=type, name=name, lane=lane, col=col, row=row)
    d.update(kw)
    return d


def F(src, tgt, name=None, **kw):
    d = dict(src=src, tgt=tgt, name=name)
    d.update(kw)
    return d


def A(id, target, text, dx, dy, w=190):
    return dict(id=id, target=target, text=text, dx=dx, dy=dy, w=w)


# helpers for explicit waypoints -------------------------------------------
def loop(src_side, y, tgt_side):
    """Back-loop: leave src from top/bottom, run at y, enter tgt top/bottom."""
    def wp(n, s, t):
        p1 = s.side(src_side)
        p4 = t.side(tgt_side)
        return [p1, (s.cx, y(n)), (t.cx, y(n)), p4]
    return wp


PROCESSES = []

# ---------------------------------------------------------------------------
# Level 0 — overview
# ---------------------------------------------------------------------------
PROCESSES.append(dict(
    id="P0", file="00-overview", level=0,
    name="Sanitary Establishment License — Overview",
    pool="Municipality", lanes=None, rows=2,
    applicant_pool="Applicant (business owner)",
    nodes=[
        N("S0", "start_msg", "License application submitted", col=0),
        N("C1", "call", "1 Register application and survey site", col=1, calls="01-register-and-survey"),
        N("C2", "call", "2 Collect technical opinions", col=2, calls="02-technical-opinions"),
        N("C3", "call", "3 Inspect premises", col=3, calls="03-site-inspection"),
        N("C4", "call", "4 Commission review and fee collection", col=4, calls="04-commission-and-fee"),
        N("C5", "call", "5 Executive approval", col=5, calls="05-executive-approval"),
        N("C6", "call", "6 License and inform applicant", col=6, calls="06-licensing"),
        N("E0", "end", "License issued", col=7),
        N("B3a", "boundary_error", "Zoning rejected", attach="C3", bx=-32, error="Err_Zoning"),
        N("B3b", "boundary_error", "Failed second inspection", attach="C3", bx=32, error="Err_Second"),
        N("B4", "boundary_error", "Rejected by commission", attach="C4", bx=0, error="Err_Commission", added_step=True,
          basis="Commission rejection path, confirmed by the author"),
        N("B5a", "boundary_error", "Cancelled by deputy mayor level", attach="C5", bx=-32, error="Err_Deputy"),
        N("B5b", "boundary_error", "Cancelled at mayor level", attach="C5", bx=32, error="Err_Mayor"),
        N("GC", "gw_x", None, col=6.5, row=1),
        N("C7", "call", "C Cancel license and close premises", col=7.5, row=1, calls="07-cancellation-and-closure", added_step=True,
          basis="Art. 13: license cancelled and premises closed"),
        N("EC", "end", "Premises closed", col=8.5, row=1),
    ],
    flows=[
        F("S0", "C1"), F("C1", "C2"), F("C2", "C3"), F("C3", "C4"),
        F("C4", "C5"), F("C5", "C6"), F("C6", "E0"),
        F("B3a", "GC", "Zoning", lab="left", added=True),
        F("B3b", "GC", "2nd inspection", added=True),
        F("B4", "GC", "Commission", added=True),
        F("B5a", "GC", "Deputy mayor", lab="left", added=True),
        F("B5b", "GC", "Mayor", added=True),
        F("GC", "C7", added=True), F("C7", "EC", added=True),
    ],
    messages=[
        ("APP", "S0", "Application", 0),
        ("C1", "APP", "Info e-mail, accrual invitation", 0),
        ("C3", "APP", "Cancellation notice", 0),
        ("C4", "APP", "Info e-mail, accrual invitation", -22),
        ("APP", "C4", "Fee payment", 22),
        ("C5", "APP", "Cancellation e-mail", 0),
        ("C6", "APP", "License approval notice", 0),
        ("C7", "APP", "Closure notice", 0),
    ],
    annotations=[
        A("a1", "S0", "Business is usually already operating when it applies (as-is practice). Art. 6: premises opened without a license are closed.", -135, 75, 205),
    ],
    groups=[dict(id="g1", label="Art. 13 — finalising inspection within 1 month", nodes=["C1", "C2", "C3"], pad=18, extra_bottom=26)],
))

# ---------------------------------------------------------------------------
# Stage 1 — register application and survey site
# ---------------------------------------------------------------------------
PROCESSES.append(dict(
    id="P1", file="01-register-and-survey", level=1,
    name="Stage 1 — Register application and survey site",
    pool="Municipality",
    lanes=[("LD", 2), ("REC", 1), ("RE", 2), ("SYS", 1), ("CASH", 2)],
    nodes=[
        N("s", "start", "Application received (business may already be operating)", "LD", 0, 1),
        N("t1", "user", "Register documents, check debts, take declaration form", "LD", 1, 1, orig="O1"),
        N("t2", "user", "Start site survey and accrual", "RE", 2, 1, orig="O2"),
        N("g1", "gw_p", None, "RE", 3, 1),
        N("gA", "gw_x", "Accrual already done?", "RE", 4, 1, added_label=True),
        N("t3", "user", "Approve site survey", "RE", 5, 1, orig="O3"),
        N("gB", "gw_x", "Business active?", "RE", 6, 1, added_label=True),
        N("gC", "gw_x", "E-mail address registered?", "RE", 7, 1, added_label=True),
        N("t4", "send", "Send application info e-mail and accrual invitation", "SYS", 8, orig="O4"),
        N("gCm", "gw_x", None, "RE", 9, 1),
        N("gP", "gw_p", None, "RE", 10, 1),
        N("t5", "user", "Record tax accrual", "RE", 11, 1, orig="O5"),
        N("b5", "boundary_escalation", "Debt due: transfer to collection", attach="t5", bx=40, interrupting=False, escalation="Esc_Accrual", added_label=True),
        N("e5", "end", "Transferred to collection", "SYS", 11 + 40 / 170, added_label=True, lp="right"),
        N("t6", "user", "Collect payment (municipal payment system)", "CASH", 12, orig="O6"),
        N("b6", "boundary_escalation", "Debt due: transfer to collection", attach="t6", bx=40, interrupting=False, escalation="Esc_Payment", added_label=True),
        N("e6b", "end", "Transferred to collection", "CASH", 12 + 40 / 170, 1, added_label=True, lp="right"),
        N("e6", "end", "Payment collected", "CASH", 13, added_label=True),
        N("gM", "gw_x", None, "RE", 11, 0),
        N("t7", "user", "Receive license application", "REC", 5, orig="O7"),
        N("gJ", "gw_p", None, "REC", 12),
        N("t8", "user", "Review site survey and front-office work", "LD", 13, 1, orig="O8"),
        N("e1", "end", "Application registered", "LD", 14, 1),
    ],
    flows=[
        F("s", "t1"), F("t1", "t2"), F("t2", "g1"), F("g1", "gA"), F("g1", "t7"),
        F("gA", "t3", "No (label added)"),
        F("gA", "gM", "Accrual done"),
        F("t3", "gB"),
        F("gB", "gC", "Active (label added)"),
        F("gB", "gM", "Business not active"),
        F("gC", "t4", "E-mail registered"),
        F("gC", "gCm", "No (label added)"),
        F("t4", "gCm"), F("gCm", "gP"),
        F("gP", "t5"), F("gP", "gM", mode="vh"),
        F("t5", "t6"), F("b5", "e5"), F("t6", "e6"), F("b6", "e6b"),
        F("gM", "gJ", mode="hv"), F("t7", "gJ"), F("gJ", "t8"), F("t8", "e1"),
    ],
    annotations=[
        A("a1", "gA", "Gateway question and 'No' label added; source only labels the 'Accrual done' path", -330, -170, 200),
        A("a2", "t5", "Escalation markers read as 'debt due: transfer to collection', based on the source note on accrual staff collecting debts that fall due", 70, -128, 230),
        A("a3", "s", "As-is: businesses usually opened first and applied afterwards. Art. 6: premises opened without a license are closed.", -70, -118, 215),
        A("a4", "t1", "Art. 6: a receipt (Örnek 6) is issued on application. Art. 12: if the declaration meets the criteria, a declaration-based license is issued the same day.", 20, -118, 300),
    ],
))

# ---------------------------------------------------------------------------
# Stage 2 — technical opinions (fire, address, zoning)
# ---------------------------------------------------------------------------
PROCESSES.append(dict(
    id="P2", file="02-technical-opinions", level=1,
    name="Stage 2 — Collect technical opinions",
    pool="Municipality",
    lanes=[("LD", 2), ("ZDIR", 2), ("GIS", 1), ("DEP", 1)],
    nodes=[
        N("s", "start", "Office review completed", "LD", 0, 1),
        N("gS", "gw_p", None, "LD", 1, 1),
        N("gF", "gw_x", "Fire report needed?", "LD", 2, 1, added_label=True),
        N("tF", "user", "Request fire department report", "LD", 3, 0, orig="O9"),
        N("gFm", "gw_x", None, "LD", 4, 1),
        N("tZ", "user", "Query zoning status", "ZDIR", 2, 0, orig="O13"),
        N("cZ", "call", "Prepare zoning opinions", "ZDIR", 3, 0, calls="02a-zoning-opinions"),
        N("tG1", "user", "Determine current address", "GIS", 2, orig="O10"),
        N("tG2", "user", "Approve address determination", "ZDIR", 3, 1, orig="O11"),
        N("tG3", "user", "Approve address determination", "DEP", 4, orig="O12"),
        N("gJ", "gw_p", None, "ZDIR", 6, 0),
        N("e", "end", "Technical opinions completed", "ZDIR", 7, 0),
    ],
    flows=[
        F("s", "gS"), F("gS", "gF"), F("gS", "tZ"), F("gS", "tG1"),
        F("gF", "tF", "Needed (label added)"),
        F("gF", "gFm", "Fire report not needed"),
        F("tF", "gFm"), F("gFm", "gJ", mode="hv"),
        F("tZ", "cZ"), F("cZ", "gJ"),
        F("tG1", "tG2"), F("tG2", "tG3"), F("tG3", "gJ", mode="hv"),
        F("gJ", "e"),
    ],
    annotations=[
        A("a2", "cZ", "Opens Stage 2a: building inspection and mapping branches plus the deputy mayor approval, unchanged", 90, -100, 240),
    ],
))

# ---------------------------------------------------------------------------
# Stage 2a — zoning opinions (two parallel review branches)
# No lanes here: the two branches share roles and their review loops would
# cross every lane. Roles stay in task names, as in the source.
# ---------------------------------------------------------------------------
_R = 140  # row height used below
PROCESSES.append(dict(
    id="P2a", file="02a-zoning-opinions", level=2,
    name="Stage 2a — Prepare zoning opinions",
    pool="Municipality", lanes=None, rows=5, rowh=_R,
    nodes=[
        N("s", "start", "Zoning status queried", col=0, row=2),
        N("gP", "gw_p", None, col=1, row=2),
        # left branch: building inspection
        N("tL1", "user", "Building Inspection Chief — handle request", col=2, row=1, orig="O14", interpreted=True),
        N("gL1", "gw_x", None, col=3, row=1),
        N("tL2", "user", "Rapporteur — prepare report", col=4, row=1, orig="O15", interpreted=True),
        N("gL2", "gw_x", None, col=5, row=1),
        N("tL3", "user", "Building Inspection Chief — review report", col=6, row=1, orig="O16", interpreted=True),
        N("xL1", "gw_x", "Chief decision?", col=7, row=1, added_label=True),
        N("gL3", "gw_x", None, col=8, row=1),
        N("tL4", "user", "Zoning Director — approve opinion", col=9, row=1, orig="O17", interpreted=True),
        N("xL2", "gw_x", "Director decision?", col=10, row=1, added_label=True),
        # right branch: mapping
        N("tR1", "user", "Mapping Chief — handle request", col=2, row=3, orig="O18", interpreted=True),
        N("gR1", "gw_x", None, col=3, row=3),
        N("tR2", "user", "Rapporteur — prepare report", col=4, row=3, orig="O19", interpreted=True),
        N("gR2", "gw_x", None, col=5, row=3),
        N("tR3", "user", "Building Inspection Chief — review report", col=6, row=3, orig="O20", interpreted=True),
        N("xR1", "gw_x", "Chief decision?", col=7, row=3, added_label=True),
        N("gR3", "gw_x", None, col=8, row=3),
        N("tR4", "user", "Zoning Director — approve opinion", col=9, row=3, orig="O21", interpreted=True),
        N("xR2", "gw_x", "Director decision?", col=10, row=3, added_label=True),
        # deputy mayor
        N("gJ", "gw_p", None, col=11, row=2),
        N("tD", "user", "Deputy Mayor — approve zoning opinions", col=12, row=2, orig="O22", interpreted=True),
        N("xD", "gw_x", "Deputy mayor decision?", col=13, row=2, added_label=True),
        N("e", "end", "Zoning opinions approved", col=13, row=1, lp="right"),
        N("gPB", "gw_p", None, col=14, row=2),
    ],
    flows=[
        F("s", "gP"), F("gP", "tL1"), F("gP", "tR1"),
        F("tL1", "gL1", mode="hv"), F("gL1", "tL2"), F("tL2", "gL2", mode="hv"),
        F("gL2", "tL3"), F("tL3", "xL1"),
        F("xL1", "gL3", "Approved"),
        F("xL1", "gL1", "Rejected", wp=loop("T", lambda n: n.rowy(1) - 70, "T")),
        F("gL3", "tL4"), F("tL4", "xL2"),
        F("xL2", "gJ", "Approved", mode="hv"),
        F("xL2", "gL2", "Rejected", wp=loop("B", lambda n: n.rowy(1) + 70, "B")),
        F("tR1", "gR1", mode="hv"), F("gR1", "tR2"), F("tR2", "gR2", mode="hv"),
        F("gR2", "tR3"), F("tR3", "xR1"),
        F("xR1", "gR3", "Approved"),
        F("xR1", "gR1", "Rejected", wp=loop("B", lambda n: n.rowy(3) + 70, "B")),
        F("gR3", "tR4"), F("tR4", "xR2"),
        F("xR2", "gJ", "Approved", mode="hv"),
        F("xR2", "gR2", "Rejected", wp=loop("T", lambda n: n.rowy(3) - 70, "T")),
        F("gJ", "tD"), F("tD", "xD"),
        F("xD", "e", "Approved"),
        F("xD", "gPB", "Rejected"),
        F("gPB", "gL3", wp=loop("T", lambda n: n.rowy(1) - 105, "T")),
        F("gPB", "gR3", wp=loop("B", lambda n: n.rowy(3) + 105, "B")),
    ],
    annotations=[
        A("a1", "tR3", "Kept as drawn: 'Yapı Denetim Şefi' (the branch starts with the Mapping Chief, so 'Harita Şefi' may have been meant; these are municipal titles, not defined in the regulation)", 70, 75, 260),
        A("a2", "tL1", "Source labels these tasks with the role only; the action wording is interpreted", -60, -120, 220),
    ],
))

# ---------------------------------------------------------------------------
# Stage 3 — site inspection
# ---------------------------------------------------------------------------
PROCESSES.append(dict(
    id="P3", file="03-site-inspection", level=1,
    name="Stage 3 — Inspect premises",
    pool="Municipality",
    lanes=[("LD", 2), ("INSP", 1), ("SYS", 2)],
    nodes=[
        N("s", "start", "Technical opinions completed", "LD", 0),
        N("t1", "user", "Start site inspection", "LD", 1, orig="O23"),
        N("xZ", "gw_x", "Zoning status?", "LD", 2, added_label=True),
        N("xM1", "gw_x", "E-mail address registered?", "SYS", 2, 1, added_label=True),
        N("t2s", "send", "Send zoning-based cancellation notice", "SYS", 3, 1, orig="O24"),
        N("xM1m", "gw_x", None, "SYS", 4, 1),
        N("eZ", "end_error", "Cancelled — zoning status", "SYS", 5, 1, error="Err_Zoning"),
        N("t2", "user", "Carry out site inspection", "LD", 3, orig="O25"),
        N("xI", "gw_x", "Inspection result?", "LD", 4, added_label=True),
        N("tN", "send", "Send deficiency notice (SMS or e-mail)", "SYS", 5, 0, added_step=True,
          basis="Art. 13 (15-day period); automated notice confirmed by the author"),
        N("tm", "timer", "15 days", "LD", 5, 1, orig="T1", lp="left"),
        N("t3", "user", "Start second site inspection", "LD", 6, 1, orig="O26"),
        N("t4", "user", "Carry out second site inspection", "INSP", 7, orig="O27"),
        N("xI2", "gw_x", "Second inspection result?", "INSP", 8, added_label=True),
        N("t5", "user", "Cancel application after second inspection", "LD", 9, 1, orig="O28"),
        N("xM2", "gw_x", "E-mail address registered?", "SYS", 10, 0, added_label=True),
        N("t6", "send", "Send application cancellation notice", "SYS", 11, 0, orig="O29"),
        N("xM2m", "gw_x", None, "SYS", 12, 0),
        N("eD", "end_error", "Cancelled — after second inspection", "SYS", 13, 0, error="Err_Second"),
        N("gP", "gw_x", None, "LD", 10),
        N("e", "end", "Ready for commission review", "LD", 11),
    ],
    flows=[
        F("s", "t1"), F("t1", "xZ"),
        F("xZ", "xM1", "Zoning rejected"),
        F("xZ", "t2", "Zoning approved"),
        F("xM1", "t2s", "Yes (label added)"),
        F("xM1", "xM1m", "No (label added)", wp=loop("B", lambda n: n.rowy_of("SYS", 1) + 50, "B")),
        F("t2s", "xM1m"), F("xM1m", "eZ"),
        F("t2", "xI"),
        F("xI", "gP", "Passed (label added)", wp=lambda n, s, t: [s.side("T"), (s.cx, n.lane_top("LD") + 16), (t.cx, n.lane_top("LD") + 16), t.side("T")]),
        F("xI", "tN", "Correction needed (label added)", wp=lambda n, s, t: [s.side("B"), (s.cx, t.cy), t.side("L")]),
        F("tN", "tm", added=True),
        F("tm", "t3"), F("t3", "t4"), F("t4", "xI2"),
        F("xI2", "gP", "Passed (label added)", wp=lambda n, s, t: [s.side("T"), (s.cx, t.cy), t.side("L")]),
        F("xI2", "t5", "Failed (label added)", mode="hv"),
        F("t5", "xM2", mode="hv"),
        F("xM2", "t6", "Yes (label added)"),
        F("xM2", "xM2m", "No (label added)", wp=loop("B", lambda n: n.lane_y("SYS") + 50, "B")),
        F("t6", "xM2m"), F("xM2m", "eD"),
        F("gP", "e"),
    ],
    annotations=[
        A("a1", "tN", "Added on the author's confirmation: the system sends the deficiency notice automatically by SMS or e-mail", 75, -38, 230),
        A("a2", "t1", "Art. 13: reach this step within 1 month of the declaration-based license. In practice earlier stages finish in a few days.", -110, 62, 230),
    ],
))

# ---------------------------------------------------------------------------
# Stage 4 — commission review and fee collection
# ---------------------------------------------------------------------------
PROCESSES.append(dict(
    id="P4", file="04-commission-and-fee", level=1,
    name="Stage 4 — Commission review and fee collection",
    pool="Municipality",
    lanes=[("LD", 1), ("SYS", 2), ("ACC", 2), ("CASH", 2)],
    nodes=[
        N("s", "start", "Ready for commission review", "LD", 0),
        N("t1", "user", "Evaluate in licensing commission", "LD", 1, orig="O30"),
        N("gK", "gw_x", "Commission decision?", "LD", 2, added_step=True, basis="Commission rejection path, confirmed by the author"),
        N("tK", "send", "Send commission rejection notice", "SYS", 2, 1, added_step=True, basis="Commission rejection path, confirmed by the author"),
        N("eK", "end_error", "Rejected by commission", "SYS", 3, 1, error="Err_Commission", added_step=True,
          basis="Commission rejection path, confirmed by the author"),
        N("xM", "gw_x", "E-mail address registered?", "LD", 3, added_label=True),
        N("t2", "send", "Send info e-mail and accrual invitation", "SYS", 4, orig="O31"),
        N("xMm", "gw_x", None, "LD", 5),
        N("t3", "user", "Create license fee accrual", "ACC", 6, orig="O32"),
        N("p1", "gw_p", None, "ACC", 7),
        N("ee1", "end_escalation", "Debt due: transfer to collection", "ACC", 7, 1, escalation="Esc_Accrual", added_label=True, lp="right"),
        N("t4", "user", "Collect license fee", "CASH", 8, orig="O33"),
        N("p2", "gw_p", None, "CASH", 9),
        N("ee2", "end_escalation", "Debt due: transfer to collection", "CASH", 9, 1, escalation="Esc_Payment", added_label=True, lp="right"),
        N("e", "end", "License fee collected", "CASH", 10),
    ],
    flows=[
        F("s", "t1"), F("t1", "gK", added=True),
        F("gK", "xM", "Approved", added=True),
        F("gK", "tK", "Rejected", added=True),
        F("tK", "eK", added=True),
        F("xM", "t2", "Yes (label added)"),
        F("xM", "xMm", "No e-mail registered"),
        F("t2", "xMm", mode="hv"),
        F("xMm", "t3", mode="z"),
        F("t3", "p1"), F("p1", "ee1"),
        F("p1", "t4", mode="hv"),
        F("t4", "p2"), F("p2", "ee2"), F("p2", "e"),
    ],
    annotations=[
        A("a1", "t1", "Commission is internal practice, not required by the regulation for sıhhi premises. Rejection path added on the author's confirmation.", -130, 70, 230),
        A("a2", "p1", "Parallel gateways make the source's double outgoing arrows explicit. Escalations read as 'debt due: transfer to collection'.", 40, -128, 230),
    ],
))

# ---------------------------------------------------------------------------
# Stage 5 — executive approval (deputy mayor, mayor) with both cancellation paths
# ---------------------------------------------------------------------------
PROCESSES.append(dict(
    id="P5", file="05-executive-approval", level=1,
    name="Stage 5 — Executive approval",
    pool="Municipality",
    lanes=[("LD", 2), ("DEP", 1), ("MAY", 2), ("SYS", 1)],
    nodes=[
        N("s", "start", "License fee collected", "LD", 0, 1),
        N("t1", "user", "Process license approval", "LD", 1, 1, orig="O34"),
        N("gM1", "gw_x", None, "DEP", 2),
        N("t2", "user", "Approve license", "DEP", 3, orig="O35"),
        N("g1", "gw_x", "Deputy mayor decision?", "DEP", 4, added_label=True),
        N("t3", "user", "Inform about cancellation of the application", "LD", 5, 0, orig="O36"),
        N("g2", "gw_x", "Cancel or resubmit?", "LD", 6, 0, added_label=True),
        N("t4", "user", "Process cancellation notification", "MAY", 7.5, 1, orig="O37"),
        N("g3", "gw_x", "E-mail address registered?", "MAY", 8.5, 1, added_label=True),
        N("t5", "send", "Send cancellation e-mail", "SYS", 9.5, orig="O38"),
        N("g3m", "gw_x", None, "SYS", 10.5),
        N("eA", "end_error", "Cancelled — deputy mayor level", "SYS", 11.5, error="Err_Deputy"),
        N("gM2", "gw_x", None, "MAY", 5, 0),
        N("t6", "user", "Approve license", "MAY", 6, 0, orig="O39"),
        N("g5", "gw_x", "Mayor decision?", "MAY", 7, 0, added_label=True),
        N("e", "end", "License approved", "MAY", 8, 0),
        N("t7", "user", "Inform about application cancellation", "LD", 8, 0, orig="O40"),
        N("g6", "gw_x", "Cancel or resubmit?", "LD", 9, 0, added_label=True),
        N("eB", "end_error", "Cancelled — mayor level", "LD", 10, 0, error="Err_Mayor"),
    ],
    flows=[
        F("s", "t1"), F("t1", "gM1", mode="z"), F("gM1", "t2"), F("t2", "g1"),
        F("g1", "t3", "Cancel", wp=lambda n, s, t: [s.side("T"), (s.cx, t.cy), t.side("L")]),
        F("g1", "gM2", "Approve", mode="hv"),
        F("t3", "g2"),
        F("g2", "t4", "Cancel application", wp=lambda n, s, t: [s.side("R"), (s.cx + 105, s.cy), (s.cx + 105, t.cy), t.side("L")]),
        F("g2", "gM1", "Resubmit (label added)", wp=loop("T", lambda n: n.lane_top("LD") + 16, "T")),
        F("t4", "g3"),
        F("g3", "t5", "Yes (label added)"),
        F("g3", "g3m", "No (label added)", mode="hv"),
        F("t5", "g3m"), F("g3m", "eA"),
        F("gM2", "t6"), F("t6", "g5"),
        F("g5", "e", "Approve"),
        F("g5", "t7", "Cancel", wp=lambda n, s, t: [s.side("T"), (s.cx, t.cy), t.side("L")]),
        F("t7", "g6"),
        F("g6", "eB", "Cancel application"),
        F("g6", "gM2", "Resubmit for approval", wp=loop("B", lambda n: n.rowy_of("MAY", 0) + 58, "B")),
    ],
    annotations=[
        A("a1", "t2", "Two-level approval is internal practice. Art. 6: the license is signed by the head of the authority or a delegate.", -150, -118, 240),
    ],
))

# ---------------------------------------------------------------------------
# Stage 6 — licensing and notification
# ---------------------------------------------------------------------------
PROCESSES.append(dict(
    id="P6", file="06-licensing", level=1,
    name="Stage 6 — License and inform applicant",
    pool="Municipality",
    lanes=[("RAP", 1), ("SYS", 1)],
    nodes=[
        N("s", "start", "License approved", "RAP", 0),
        N("t1", "user", "License the business and inform the citizen", "RAP", 1, orig="O41"),
        N("x", "gw_x", "E-mail address registered?", "RAP", 2, added_label=True),
        N("t2", "send", "Send license approval notice", "SYS", 3, orig="O42"),
        N("xm", "gw_x", None, "RAP", 4),
        N("e", "end", "License issued", "RAP", 5),
    ],
    flows=[
        F("s", "t1"), F("t1", "x"),
        F("x", "t2", "Yes (label added)"),
        F("x", "xm", "No (label added)"),
        F("t2", "xm", mode="hv"), F("xm", "e"),
    ],
    annotations=[
        A("a1", "t1", "Issues the finalised license: the declaration-based license becomes final after the inspection (Art. 13).", -100, 62, 250),
    ],
))

# ---------------------------------------------------------------------------
# Stage C — cancellation and closure (NOT in the source diagram)
# Added on the author's instruction: the business is already operating, so a
# cancelled license ends with closure. Software view: the cancellation notice
# becomes a work order for the municipal police; sealing happens on site
# (manual task) and is confirmed in the system (user task).
# ---------------------------------------------------------------------------
PROCESSES.append(dict(
    id="P7", file="07-cancellation-and-closure", level=1,
    name="Stage C — Cancel license and close premises",
    pool="Municipality",
    lanes=[("SYS", 1), ("ZAB", 2)],
    nodes=[
        N("s", "start", "License cancelled", "SYS", 0),
        N("t1", "service", "Create closure work order for municipal police", "SYS", 1, added_step=True,
          basis="Art. 13: license cancelled and premises closed"),
        N("t2", "manual", "Serve closure notice and seal premises (on site)", "ZAB", 2, added_step=True,
          basis="Art. 13; notice served under Tebligat Kanunu 7201"),
        N("t3", "user", "Confirm closure in system", "ZAB", 3, added_step=True,
          basis="Software workflow: closes the case"),
        N("e", "end", "Premises closed", "ZAB", 4),
    ],
    flows=[F("s", "t1", added=True), F("t1", "t2", added=True), F("t2", "t3", added=True), F("t3", "e", added=True)],
    annotations=[
        A("a1", "t1", "Not drawn in the source. Triggered by any of the four cancellation outcomes.", 80, -52, 220),
        A("a2", "t2", "The business may challenge the decision in administrative court; that route is out of scope.", 40, 58, 250),
    ],
))
