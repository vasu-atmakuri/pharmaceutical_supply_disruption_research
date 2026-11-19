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
