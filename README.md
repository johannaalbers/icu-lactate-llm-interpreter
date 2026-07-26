# AI Clinical Statistics Interpreter

**Turning logistic regression output into a publication-style clinical results paragraph — using an LLM.**

A small end-to-end health data science pipeline: extract an ICU cohort from MIMIC-III, fit a multivariable logistic regression, and use a large language model to translate the model output (odds ratios, confidence intervals, p-values) into the kind of prose you would find in the results section of a clinical paper.

> **No patient data is contained in this repository.** See [Data access and compliance](#data-access-and-compliance).

---

## Research question

**Are elevated lactate levels associated with ICU mortality?**

Retrospective cohort study on MIMIC-III. Unit of analysis is the ICU stay. For each stay, the first lactate measurement within 24 hours of ICU admission was extracted; the outcome is ICU mortality. The model adjusts for age at ICU discharge and sex.

## Results

Multivariable logistic regression, n = 22,302 ICU stays:

| Predictor | OR | 95% CI | p |
|---|---|---|---|
| log(lactate) | 2.82 | 2.66 – 2.99 | < 0.001 |
| Age at ICU discharge (per year) | 1.02 | 1.02 – 1.03 | < 0.001 |
| Sex (male vs. female) | 0.97 | 0.90 – 1.05 | 0.49 |

Pseudo R² = 0.083. Higher lactate and older age were independently associated with greater odds of ICU death; sex was not.

The full model output is in [`icu_lactate_logistic_model_results.csv`](icu_lactate_logistic_model_results.csv) and the LLM-generated interpretation in [`interpretation_results.txt`](interpretation_results.txt).

## Pipeline

```text
MIMIC-III (local, credentialed)
        ↓  SQL cohort extraction
Cohort (stays with early lactate)   ←— stays local, never committed
        ↓  cleaning + log transform
Logistic regression (statsmodels)
        ↓
Aggregate results table (OR, CI, p, n)   ←— the only thing that leaves the machine
        ↓  structured prompt
Large language model
        ↓
Clinical interpretation paragraph
```

## Repository contents

| File | Description |
|---|---|
| `icu-lactate-data-extraction.ipynb` | SQL cohort extraction from MIMIC-III. Writes `cohort_export.csv` locally (git-ignored). |
| `icu-lactate-mortality-analysis.ipynb` | Cleaning, EDA, logistic regression, prompt construction, LLM call. |
| `icu_lactate_logistic_model_results.csv` | Aggregate model results. No patient-level data. |
| `interpretation_results.txt` | LLM-generated interpretation of the results above. |
| `.env.example` | Template for the required environment variables. |

## Setup

```bash
git clone https://github.com/<your-username>/icu-lactate-llm-interpreter.git
cd icu-lactate-llm-interpreter

python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt

cp .env.example .env      # then fill in your own credentials
```

Run `icu-lactate-data-extraction.ipynb` first (produces the local cohort file), then `icu-lactate-mortality-analysis.ipynb`.

## Data access and compliance

This project uses the **MIMIC-III Clinical Database**, which is *credentialed access* data distributed by PhysioNet. This repository therefore contains **only code and aggregate statistics** — no cohort file, no patient-level rows, no notebook outputs showing individual records.

To reproduce the analysis you need to obtain access yourself:

1. Complete the CITI "Data or Specimens Only Research" training.
2. Become a credentialed PhysioNet user and sign the [PhysioNet Credentialed Health Data Use Agreement 1.5.0](https://physionet.org/about/licenses/physionet-credentialed-health-data-license-150/).
3. Load MIMIC-III into your own database instance and point `.env` at it.

**On the LLM step.** PhysioNet's guidance on [responsible use of MIMIC data with online services](https://physionet.org/news/post/gpt-responsible-use/) states that the DUA prohibits sending credentialed data to third-party APIs. This pipeline is designed around that constraint: the model receives **only aggregate summary statistics** (variable names, odds ratios, confidence intervals, p-values, sample size) — never a row, an identifier, a date or a free-text note. If you intend to extend this project to anything patient-level, use a route PhysioNet lists as acceptable (Azure OpenAI with human review opted out, Amazon Bedrock, Vertex AI, Anthropic Claude) or a locally hosted model.

## Citation

If you use MIMIC-III, cite:

> Johnson, A. E. W., Pollard, T. J., Shen, L., Lehman, L. H., Feng, M., Ghassemi, M., Moody, B., Szolovits, P., Celi, L. A., & Mark, R. G. (2016). MIMIC-III, a freely accessible critical care database. *Scientific Data*, 3, 160035.

> Goldberger, A., Amaral, L., Glass, L., Hausdorff, J., Ivanov, P. C., Mark, R., ... & Stanley, H. E. (2000). PhysioBank, PhysioToolkit, and PhysioNet: Components of a new research resource for complex physiologic signals. *Circulation*, 101(23), e215–e220.

## Limitations

Observational, single-centre, retrospective. Associations only — no causal claims. Age is derived from year differences and capped at 90 (MIMIC-III shifts ages above 89). Values reported as "greater than" the assay limit were set to 31 mmol/L. The model is deliberately minimal (three predictors) and is not adjusted for severity of illness, admission diagnosis or treatment, so residual confounding is substantial.

## Disclaimer

Educational and research portfolio project. Not a medical device, not clinical decision support, and not medical advice. LLM-generated text is not a substitute for expert statistical or clinical review and should always be checked against the underlying model output.

## License

Code released under the MIT License (see [`LICENSE`](LICENSE)). The license covers this repository's code only — it does not grant any rights to MIMIC-III data, which remains governed by the PhysioNet DUA.

---

**Author:** Johanna Albers — Health Data Science & AI projects
