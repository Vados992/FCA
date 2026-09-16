# Numerical methods and interpretation

All methods execute real calculations on the submitted rows. Algorithms use only the Python standard library. Every row needs a unique string `id`; parsing accepts JSON numbers and numerical CSV strings where the method requires numbers. Nonfinite values and booleans as numeric parameters are rejected. The adapter registry exposes exact allowed parameter names through `GET /v1/adapters`.

## Policy and public health

**RCT** estimates `mean(Y | treatment=1) - mean(Y | treatment=0) - bias_offset`. Treatment is binary, rows are independent sampling units, and both arms require at least two observations. Each bootstrap draw resamples within each arm. Identification requires evidence for random assignment, consistency and no interference, an explicit acyclic causal graph and estimand ATE. A declared parent of randomized treatment is rejected by this implementation. Public-health RCT additionally requires evidence for ethics/consent, measurement and selection assumptions; it is a research tool, not clinical decision support.

**DiD** estimates the treated/control difference in individual `Y_post - Y_pre` changes, with a second earlier observation for the preregistered pretrend-tolerance diagnostic. Bootstrap units preserve each individual's paired observations. Identification requires parallel trends, no anticipation, no interference and stable composition; estimand ATT. Passing the pretrend tolerance does not prove parallel counterfactual trends. Staggered adoption, clustered assignment, spillovers, panel attrition corrections and heterogeneous group/time estimators are outside this method.

**IV** computes the just-identified slope `cov(Z,Y) / cov(Z,X) - bias_offset`; bootstrap resamples complete `(Z,X,Y)` rows. It records a first-stage F diagnostic and rejects a weak first stage at G8 using the frozen threshold. Identification for LATE requires exclusion, instrument independence and monotonicity, an explicit `Z → X → Y` path, and no declared `Z → Y` path bypassing X. Structural checks cannot rule out omitted confounding. This is one instrument/one exposure, no covariates or multivariable 2SLS. A finite first-stage threshold is a diagnostic rather than proof of instrument validity.

**Intervals** are percentile bootstrap intervals using Python's local `random.Random(seed)`. Between 100 and 2,000 draws and a bounded resampling budget are allowed. The usual 0.05 alpha gives a 95% interval. The positive-direction operational claim is supported only if the lower endpoint exceeds the frozen nonnegative effect threshold; a wholly opposite interval falsifies that directional claim; overlap is inconclusive. Sampling uncertainty is separate from the declared bias scenario and unmeasured confounding. Rows with time/cluster dependence need a different reviewed adapter.

## Science

`prediction_check` evaluates fixed, externally supplied predictions using standardized residuals `(observed - predicted - prediction_offset) / sigma`. Positive measurement standard deviations and a frozen maximum absolute residual threshold are required. Chi-square is reported as a diagnostic sum, not a calibrated p-value after model fitting. The maximum criterion requires a justified family-aware threshold. Compatibility within supplied rows does not establish theory truth.

`finite_predicate` counts boolean witnesses over distinct named members. `quantifier=exists` requires a witness. `quantifier=none` can certify a universal negative **only inside the explicitly named finite universe**, when `CoverageSpec` binds the exact dataset, scope populations, member key, witness column and independent coverage justification. Missing members, an unrelated observation table, duplicate identities and nonboolean witnesses block the certificate. An incomplete search cannot prove a universal negative. This is finite enumeration, not an arbitrary theorem prover.

## Market

`backtest` accepts precomputed positions and single-asset simple returns over a frozen holdout. Each period computes gross return `position * asset_return`; net return subtracts turnover `abs(position - previous_position)` times transaction plus slippage rates and short borrowing cost. Initial entry is charged. Wealth compounds `1 + net_return`; insolvency and leverage violations invalidate the model. Maximum drawdown and descriptive annualized Sharpe use the declared observation frequency, with no IID return confidence interval. **There is no terminal liquidation; the ending holding is reported.**

Training must end before holdout starts. Signal availability must precede each decision; intervals must be ordered and nonoverlapping; realized returns must precede the final research cutoff. Required certificates address point-in-time universe, survivorship and capacity. Calendar-daily synthetic examples use 365 periods/year. Real trading-calendar frequency, borrow, impact, corporate actions, financing and point-in-time data require explicit modeling. There is no broker connection or order execution.

## Supply

`max_flow` implements Edmonds–Karp for a directed single-commodity capacity network with source and sink. It reports flow, residual minimum cut, edge utilization and conservation checks. A counterfactual can disable named edges. Parallel/antiparallel edges are rejected; represent distinct transport choices with intermediate nodes. Bounds: 500 nodes, 3,000 edges and 10,000 augmentations; positive capacities below `1e-9` must be rescaled. Multi-commodity, dynamic inventory, cost minimization and uncertainty in capacities are outside this method.

## Climate

`single_fingerprint_iid` fits `observed = intercept + beta * (forcing_scale * fixed_fingerprint) + error` by OLS. At least 30 rows and independent residuals are required. It reports an asymptotic normal interval for beta; positive lower endpoint supports the specific association. A fixed fingerprint, measurement-validity and residual-independence certificates are required. This is not multi-forcing attribution, generalized least squares, autocorrelation-aware optimal fingerprinting or a climate policy conclusion. Typical correlated climate time series need a different method.

## Physics

`oscillator_recurrence` validates an ordered harmonic oscillator trajectory `(t,x,v)` against the fixed-frequency analytical solution. It checks normalized trajectory residual, relative energy drift, elapsed periods and final phase-space distance from the initial state. The zero-energy stationary case is rejected as a periodic-orbit witness. Frozen measurement/model/closure tolerances define the tested regime. Phase-space recurrence is not a closed timelike curve, general relativity simulation or a time-travel certificate.

## Integrity

`documentary_path` runs bounded breadth-first search over recorded payments, ownership, contracts and access edges. It reports the actual path and maximum hop count. Evidence establishes what the registered documentary source says; source hashes do not establish the source's truth. No legal guilt, motive, intent, control, influence or causal conclusion follows from path existence.

## Shared research controls

Counterfactuals are evidence-backed, preregistered alternative parameter scenarios. They do not automatically constitute intervention identification. Every declared scenario runs and is retained; changes to alpha, bootstrap sample count, direction or effect threshold are disallowed as counterfactuals. Sign stability is descriptive. Causal, mechanism and quantified claims must also retain the same operational scientific state across the ensemble.

Falsification tests support mean, maximum absolute value, group difference, count and an asymptotic two-sided mean z-test (`n >= 30`). Non-rejection of a negative control is not an equivalence certificate. Holm controls a frozen test family under its usual conditions; Benjamini–Hochberg needs its usual independence/positive-dependence assumptions and is not a blanket arbitrary-dependence guarantee. Multiple statistical tests cannot use the `none` correction. Protocol alpha controls adjusted-p acceptance; the `TestSpec.threshold` is the bound for non-p-value metrics.

Model-target control failure invalidates the model for this run; it is not automatically substantive falsification of the hypothesis. Hypothesis-target failure is separately recorded. Material contradictory evidence blocks promotion unless a reviewed, evidence-bearing resolution exists. A reviewer cannot change the frozen machine verdict.

Same-environment reproduction compares numerical trees using the frozen `atol + rtol * abs(reference)` rule, with exact equality by default. Code, interpreter and platform are reported. Cross-version Python or platform changes can change floating-point/bootstrap results; the result must be rerun under its recorded environment or use explicitly preregistered tolerances. Successful replay is reproducibility of computation, not independent external scientific replication.
