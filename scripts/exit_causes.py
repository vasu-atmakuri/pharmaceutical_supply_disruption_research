"""What each observed near-sole exit actually was, keyed to the exact event.

Keyed on (market, event quarter, departing labeler). The previous version matched on
an ingredient substring, which silently gave Assertio's 2022Q4 diclofenac potassium
oral liquid the evidence from Teva's 2019 oral tablet shortage: a different firm, a
different formulation and a different period. A growing cohort makes substring
matching unsafe, so an event is classified only by exact identity and anything
unlisted stays undetermined.

Classes, in descending order of how well the cause is established:

  supply        a shortage, recall or discontinuation naming this firm and period
  withdrawal    a market-wide regulatory withdrawal, firm-independent
  transition    a documented regulatory action that removes the product from the
                prescription market irrespective of supply
  coverage      the firm left the Medicaid Drug Rebate Program; the product remains
                marketed, so dispensing leaves this data source and not the market
  transfer      marketing rights moved to another firm; supply continued
  artefact      the market key is a misspelling of a real multi-supplier market, so
                the apparent sole supplier is a measurement error
  continued     a labeler absent before the exit supplies the market afterwards, so
                the market was not left unsupplied, but no record names why this
                firm left
  undetermined  no record found for this firm and period
"""

CAUSES={
 ("RANITIDINE | ORAL TABLET","2020Q2","53746"): ("withdrawal",
  "FDA requested withdrawal of all ranitidine, 1 Apr 2020 (NDMA); market-wide and firm-independent"),
 ("TARTRATE,VARENICLINE | OTHER","2021Q3","00069"): ("supply",
  "Pfizer recalled all lots for nitrosamine content, Sep 2021; FDA recorded a varenicline shortage"),
 ("VARENICLINE | ORAL TABLET","2021Q4","00069"): ("supply",
  "Same recall episode as the 2021Q3 varenicline exit, affecting a second formulation"),
 ("HYDROCHLORIDE,OLOPATADINE | OPHTHALMIC","2021Q3","62332"): ("transition",
  "Rx-to-OTC switch approved for the brand from Feb 2020; no firm-level record of why this labeler left"),
 ("ALCAFTADINE | OPHTHALMIC","2022Q2","00023"): ("transition",
  "Rx-to-OTC switch approved for the brand Dec 2021, retail Mar 2022; no firm-level record of why this labeler left"),
 ("4,ELEMENTS,TRACE | INJECTABLE #94f1","2022Q1","00517"): ("transition",
  "American Regent retired its unapproved Multitrace line under FDA's unapproved drugs "
  "initiative and replaced it with the approved Tralement and Multrys; the successor "
  "dispenses in a sibling key the composition tie-break holds apart"),
 ("GOSERELIN | INJECTABLE","2021Q4","70720"): ("coverage",
  "TerSera withdrew from the Medicaid Drug Rebate Program effective 1 Oct 2021, so state "
  "programmes stopped covering its products; Zoladex remains FDA-approved and marketed"),
 ("ALIROCUMAB | INJECTABLE","2021Q2","00024"): ("transfer",
  "Regeneron took sole United States responsibility for Praluent effective 1 Apr 2020, with "
  "availability not expected to be affected; another labeler dispenses in this market afterwards"),
 ("ESCITSLOPRAM | ORAL TABLET","2024Q2","68180"): ("artefact",
  "The ingredient string is a misspelling of escitalopram; the correctly spelled oral tablet "
  "market has sixteen labelers and 51.5 million prescriptions, so this is not a single-source market"),
 ("GRISOFULVIN | ORAL LIQUID","2023Q3","69097"): ("artefact",
  "The ingredient string is a misspelling of griseofulvin; the correctly spelled oral liquid "
  "market has two labelers, so this is not a single-source market"),
}

# Events where a labeler absent before the exit supplies the market afterwards. The
# market was not left unsupplied, but no record names why this particular firm left.
CONTINUED_NOTE=("continued",
 "A labeler not present before the exit supplies this market afterwards, so the market "
 "was not left unsupplied; no shortage, withdrawal, recall or switch record names this firm")

UNDETERMINED=("undetermined",
 "No shortage, withdrawal, recall, switch or rebate-programme record found for this firm and period")

def classify(market, quarter, labeler, new_labeler_appears=False):
    k=(market,quarter,str(labeler).zfill(5))
    if k in CAUSES: return CAUSES[k]
    if new_labeler_appears: return CONTINUED_NOTE
    return UNDETERMINED

def declared_keys():
    return set(CAUSES)

# For each declared event: a short record string for the appendix table, how closely
# the record ties to the departing firm and formulation, and the issuing authority
# and date of the document relied on. Link levels, strongest first:
#
#   product and firm   the record names this firm and this formulation
#   molecule-wide      the action covers every labeler of the molecule at once, so
#                      it is firm-independent by construction
#   ingredient level   a regulatory action covers the molecule but does not name the
#                      departing firm or state why it left
#   key level          the finding is about the market key itself, not a regulatory
#                      event: the key is a misspelling of a real multi-supplier market
#   panel              the evidence is dispensing in this panel, not an outside
#                      record: a labeler absent before the exit supplies the market
#                      afterwards
#
# No URLs are stored. A URL ages faster than the record it points at, and several of
# these documents have already moved; the issuer, document and date identify each one.
RECORD={
 ("RANITIDINE | ORAL TABLET","2020Q2","53746"): (
  "Withdrawal of all ranitidine requested over NDMA; every labeler left at once",
  "molecule-wide","FDA press announcement, 1 Apr 2020"),
 ("TARTRATE,VARENICLINE | OTHER","2021Q3","00069"): (
  "All lots recalled for nitrosamine content; FDA recorded a varenicline shortage",
  "product and firm","FDA recall notice, Sep 2021; FDA drug shortage record"),
 ("VARENICLINE | ORAL TABLET","2021Q4","00069"): (
  "Second formulation in the same recall episode",
  "product and firm","FDA recall notice, Sep 2021"),
 ("HYDROCHLORIDE,OLOPATADINE | OPHTHALMIC","2021Q3","62332"): (
  "Rx-to-OTC switch approved for the brand; no firm-level record for this labeler",
  "ingredient level","FDA Rx-to-OTC switch approval, Feb 2020"),
 ("ALCAFTADINE | OPHTHALMIC","2022Q2","00023"): (
  "Rx-to-OTC switch approved for the brand; retail from Mar 2022",
  "ingredient level","FDA Rx-to-OTC switch approval, Dec 2021"),
 ("4,ELEMENTS,TRACE | INJECTABLE #94f1","2022Q1","00517"): (
  "Unapproved multi-element line retired and replaced by approved products; the "
  "successor dispenses in a sibling key",
  "product and firm","FDA unapproved drugs initiative; FDA approval of the successor products, 2020"),
 ("GOSERELIN | INJECTABLE","2021Q4","70720"): (
  "Firm left the Medicaid Drug Rebate Program, so state programmes stopped covering "
  "it; the product stayed on the market",
  "product and firm","CMS Medicaid Drug Rebate Program termination, effective 1 Oct 2021"),
 ("ALIROCUMAB | INJECTABLE","2021Q2","00024"): (
  "Marketing rights moved to the originator, availability not expected to be "
  "affected; the other firm dispenses afterwards",
  "product and firm","Company announcement of the restructured collaboration, effective 1 Apr 2020"),
 ("ESCITSLOPRAM | ORAL TABLET","2024Q2","68180"): (
  "Ingredient string is a misspelling; the correctly spelled market has sixteen "
  "labelers and 51.5 million prescriptions",
  "key level","This panel; FDA structured ingredient data"),
 ("GRISOFULVIN | ORAL LIQUID","2023Q3","69097"): (
  "Ingredient string is a misspelling; the correctly spelled market has two labelers",
  "key level","This panel; FDA structured ingredient data"),
}

CONTINUED_RECORD=("A labeler absent before the exit supplies the market afterwards",
 "panel","This panel")
UNDETERMINED_RECORD=("None found","---","")

def record(market, quarter, labeler, new_labeler_appears=False):
    k=(market,quarter,str(labeler).zfill(5))
    if k in RECORD: return RECORD[k]
    if k in CAUSES: raise KeyError(f"{k} is classified but has no appendix record")
    if new_labeler_appears: return CONTINUED_RECORD
    return UNDETERMINED_RECORD

# Where each record can be found. The appendix previously gave the issuer and the date
# and no link, on the grounds that links rot. The reviewer's answer is the right one
# for a reproducibility paper: a document that has moved is still easier to find from a
# stale link plus an exact title than from a description. So each entry carries the
# document's exact title, its issuer, its date, and a URL where we have verified one.
# A URL appears here only if it was retrieved and read; absent means not verified, not
# nonexistent, and the title and date are then the stable identifier. Where the record
# itself names the product codes, they are recorded, because an NDC labeler segment
# alone does not identify a formulation.
SOURCES={
 ("RANITIDINE | ORAL TABLET","2020Q2","53746"): dict(
  issuer="US Food and Drug Administration",
  title="FDA Requests Removal of All Ranitidine Products (Zantac) from the Market",
  date="2020-04-01", kind="press announcement",
  url="https://www.fda.gov/news-events/press-announcements/"
      "fda-requests-removal-all-ranitidine-products-zantac-market",
  verified=True),
 ("TARTRATE,VARENICLINE | OTHER","2021Q3","00069"): dict(
  issuer="US Food and Drug Administration",
  title="Pfizer Expands Voluntary Nationwide Recall to include All Lots of CHANTIX "
        "(Varenicline) Tablets Due to N-Nitroso Varenicline Content",
  date="2021-09-16", kind="company announcement posted by FDA",
  ndc="0069-0468, 0069-0469",
  url="https://www.fda.gov/safety/recalls-market-withdrawals-safety-alerts/"
      "pfizer-expands-voluntary-nationwide-recall-include-all-lots-chantixr-"
      "varenicline-tablets-due-n",
  verified=True),
 ("VARENICLINE | ORAL TABLET","2021Q4","00069"): dict(
  issuer="US Food and Drug Administration",
  title="Pfizer Expands Voluntary Nationwide Recall to include All Lots of CHANTIX "
        "(Varenicline) Tablets Due to N-Nitroso Varenicline Content",
  date="2021-09-16", kind="company announcement posted by FDA",
  ndc="0069-0468, 0069-0469",
  url="https://www.fda.gov/safety/recalls-market-withdrawals-safety-alerts/"
      "pfizer-expands-voluntary-nationwide-recall-include-all-lots-chantixr-"
      "varenicline-tablets-due-n",
  verified=True),
 ("HYDROCHLORIDE,OLOPATADINE | OPHTHALMIC","2021Q3","62332"): dict(
  issuer="US Food and Drug Administration",
  title="FDA Approves Three Drugs for Nonprescription Use Through Rx-to-OTC Switch Process",
  date="2020-02-14", kind="press announcement", verified=False),
 ("ALCAFTADINE | OPHTHALMIC","2022Q2","00023"): dict(
  issuer="US Food and Drug Administration",
  title="Rx-to-OTC switch approval, alcaftadine ophthalmic solution 0.25% (Lastacaft)",
  date="2021-12", kind="approval", verified=False),
 ("4,ELEMENTS,TRACE | INJECTABLE #94f1","2022Q1","00517"): dict(
  issuer="US Food and Drug Administration",
  title="Unapproved Drugs Initiative; approval of trace element injection products "
        "(Tralement, Multrys)",
  date="2020", kind="approval and compliance programme", verified=False),
 ("GOSERELIN | INJECTABLE","2021Q4","70720"): dict(
  issuer="Centers for Medicare and Medicaid Services, relayed in state Medicaid "
         "pharmacy notices",
  title="Termination of the Medicaid Drug Rebate Program agreement, TerSera "
        "Therapeutics LLC, effective 1 October 2021",
  date="2021-10-01", kind="rebate agreement termination", verified=False),
 ("ALIROCUMAB | INJECTABLE","2021Q2","00024"): dict(
  issuer="Regeneron Pharmaceuticals",
  title="Restructured Praluent collaboration: Regeneron assumes sole responsibility "
        "for Praluent in the United States, effective 1 April 2020",
  date="2020-04-01", kind="company announcement", verified=False),
 ("ESCITSLOPRAM | ORAL TABLET","2024Q2","68180"): dict(
  issuer="This analysis", title="Market key comparison against FDA structured "
  "active-ingredient data", date="", kind="internal", verified=True),
 ("GRISOFULVIN | ORAL LIQUID","2023Q3","69097"): dict(
  issuer="This analysis", title="Market key comparison against FDA structured "
  "active-ingredient data", date="", kind="internal", verified=True),
}

def source_detail(market, quarter, labeler):
    """The full citation for a declared event, or an empty dict."""
    return SOURCES.get((market,quarter,str(labeler).zfill(5)), {})
