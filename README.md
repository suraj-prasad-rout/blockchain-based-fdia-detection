# FDIA Mitigation in Smart Microgrids Using Blockchain

A research prototype for evaluating **False Data Injection Attack (FDIA) detection** in a simulated smart microgrid using Weighted Least Squares (WLS) state estimation, residual-based anomaly detection, and blockchain-backed measurement-integrity verification.

> **Project status:** Core implementation and automated tests are complete. The latest recorded test run passed **33 tests**. This is a local research prototype, not a production-ready microgrid protection system.

## Contents

- [Overview](#overview)
- [Objectives](#objectives)
- [How the system works](#how-the-system-works)
- [Technology stack](#technology-stack)
- [Project structure](#project-structure)
- [Requirements](#requirements)
- [Setup on Windows](#setup-on-windows)
- [Run the experiments](#run-the-experiments)
- [Live demonstration guide](#live-demonstration-guide)
- [Results](#results)
- [Tests](#tests)
- [Limitations and security considerations](#limitations-and-security-considerations)
- [Reproducibility notes](#reproducibility-notes)
- [Future work](#future-work)

## Overview

Smart-grid monitoring and control depend on measurements from field devices and sensors. In a False Data Injection Attack, an attacker manipulates measurements to influence the estimated state of the power system.

This project builds a small simulated microgrid and evaluates two complementary mechanisms:

1. **Residual-based detection:** estimates bus voltage angles using WLS and checks whether the measurement residual statistic exceeds a detection threshold.
2. **Blockchain-backed integrity verification:** stores a cryptographic hash of a measurement payload in a Solidity smart contract. Later, the payload can be checked against the registered hash to detect changes made after registration.

The experiments compare clean measurements with random, targeted, and model-consistent attack scenarios. They also measure state-estimation error and local blockchain performance.

## Objectives

- Simulate a small electrical network using `pandapower`.
- Generate synthetic measurements and reference states.
- Estimate bus voltage angles using a DC measurement model and WLS.
- Create clean, random-attack, targeted-attack, and model-consistent-attack scenarios.
- Evaluate a residual-based anomaly detector.
- Register and verify measurement-payload hashes using a Solidity smart contract.
- Measure detection metrics, estimation error, transaction/verification latency, throughput, and gas consumption.
- Document where residual detection and hash-based integrity checks succeed and where they are insufficient.

## How the system works

```text
Simulated microgrid
        |
        v
Synthetic measurements + reference states
        |
        v
FDIA scenario generation
        |
        +------------------------------+
        |                              |
        v                              v
WLS state estimation            Canonicalize payload
        |                              |
        v                              v
Residual statistic              Cryptographic hash
        |                              |
        v                              v
Residual threshold check        Smart-contract registry
        |                              |
        v                              v
Anomaly result                  Verify against registered hash
        |                              |
        +---------------+--------------+
                        |
                        v
              Metrics and result files
```

### Main components

1. **Microgrid simulation** — builds the network and produces synthetic power-flow measurements.
2. **State estimation** — estimates bus voltage angles from measurements using WLS.
3. **Attack scenarios** — produces manipulated measurement sets for different FDIA types.
4. **Residual detector** — flags a case when the residual statistic exceeds its threshold.
5. **Smart-contract registry** — records payload hashes and supports later verification.
6. **Evaluation** — calculates metrics and writes CSV summaries and plots.

**Important distinction:** the residual detector checks measurement consistency with the implemented model. The blockchain checks whether a payload matches a previously registered hash. These are different checks and should not be treated as interchangeable.

## Technology stack

- Python 3.11
- pandapower
- NumPy and SciPy
- pandas and Matplotlib
- pytest
- Web3.py
- Solidity
- Hardhat local development blockchain
- Node.js and npm

## Project structure

```text
fdia-blockchain-microgrid/
├── artifacts/
│   ├── contract_abi.json
│   └── contract_address.json
├── contracts/
│   └── MeasurementRegistry.sol
├── data/
│   ├── raw/
│   └── processed/
├── results/
│   ├── integrated_trials.csv
│   ├── integrated_summary.csv
│   ├── integrated_residual_metrics.csv
│   └── integrated_detection_comparison.png
├── src/
│   ├── attacks/
│   ├── blockchain/
│   ├── defense/
│   ├── estimation/
│   ├── evaluation/
│   └── simulation/
├── tests/
├── hardhat.config.ts
├── package.json
├── package-lock.json
├── requirements.txt
└── README.md
```

## Requirements

- Python 3.11
- Node.js and npm
- Windows PowerShell (commands below are written for Windows)
- A local Hardhat development blockchain for blockchain-dependent experiments

## Setup on Windows

Run these commands from the project root.

### 1. Create and activate a virtual environment

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

If PowerShell blocks activation in the current terminal, you can run:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy RemoteSigned
.\.venv\Scripts\Activate.ps1
```

### 2. Install Python dependencies

```powershell
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

### 3. Install JavaScript dependencies

```powershell
npm ci
```

### 4. Compile the Solidity contract

```powershell
npx hardhat compile
```

A message such as `No contracts to compile` can be normal when the contract is already compiled and unchanged.

### 5. Start the local Hardhat node

Open a **second PowerShell terminal** in the project root and run:

```powershell
npx hardhat node
```

Keep this terminal open while running blockchain experiments.

### 6. Deploy the registry contract

In the first terminal, with `.venv` activated, run:

```powershell
python -m src.blockchain.compile_deploy
```

Use the ABI and contract address generated by the deployment script. The deployment script writes the contract artifacts used by the Python client.

> **Local-chain note:** restarting `npx hardhat node` resets its local chain state. After a restart, deploy the contract again before running blockchain experiments.

### 7. Check the blockchain connection

```powershell
python -c "from src.blockchain.registry import MeasurementRegistryClient; c=MeasurementRegistryClient(); print('Chain ID:', c.w3.eth.chain_id); print('Contract:', c.address)"
```

The local Hardhat chain ID is expected to be `31337`. The printed contract address should match the current deployment.

## Run the experiments

Run commands from the project root with the Python virtual environment activated. Blockchain commands require the Hardhat node to be running and the registry contract to be deployed.

### Baseline

```powershell
python -m src.evaluation.run_baseline
```

### WLS state estimation

```powershell
python -m src.evaluation.run_wls
```

### FDIA experiments

```powershell
python -m src.evaluation.run_experiments
```

### Register and verify measurement payloads

```powershell
python -m src.blockchain.register_batch
python -m src.blockchain.verify_batch
python -m src.blockchain.security_checks
```

### Blockchain benchmarks

```powershell
python -m src.evaluation.run_blockchain_benchmark
python -m src.evaluation.run_blockchain_fdia_experiment
```

### Integrated experiment

```powershell
python -m src.evaluation.run_integrated_experiment
```

The integrated experiment runs 100 seeds and evaluates clean, random-attack, targeted-attack, and model-consistent-attack cases. It combines WLS/residual evaluation with checks against previously registered clean payloads and records result files under `results/`.

**Avoid duplicate registrations:** the integrated experiment uses fixed batch-ID prefixes. Run it once per fresh local chain unless you intentionally change the batch-ID prefixes or reset and redeploy the local chain. The contract rejects duplicate batch/index registrations.

## Live demonstration guide

For a teacher/external demonstration, rehearse this sequence before the presentation.

1. **Show the simulated network and measurements.** Explain that this is a synthetic, software-based microgrid model rather than a physical hardware setup.
2. **Explain WLS and residual detection.** Show how the estimated state is used to calculate a residual statistic and compare it with a threshold.
3. **Show the contract deployment.** Point out the local Hardhat node, the deployed registry address, and the chain ID.
4. **Demonstrate integrity verification.** Register a clean payload, verify the unchanged payload, and then verify a modified payload against the original registered reference. A changed payload should fail the reference-hash check.
5. **Show the experimental outputs.** Open `results/integrated_detection_comparison.png`, `results/integrated_summary.csv`, and `results/integrated_residual_metrics.csv`.
6. **State the limitation clearly.** A false payload registered first can verify against its own hash. Hash verification alone cannot determine whether the original measurement was physically true.

The integrated experiment uses fixed batch IDs, so do not repeatedly run it against the same chain state. For a reliable live demo, prepare the local node and deployment beforehand and keep the saved result files available as a fallback.

## Results

The following values are from the recorded 100-seed integrated experiment and local Hardhat benchmark. They describe this particular synthetic setup; they are not guarantees of performance on a real microgrid or production blockchain.

### Residual-based detection

| Metric                                 | Recorded result |
| -------------------------------------- | --------------: |
| True positives                         |              97 |
| True negatives                         |              97 |
| False positives                        |               3 |
| False negatives                        |             203 |
| Precision                              |          97.00% |
| Recall                                 |          32.33% |
| F1-score                               |          48.50% |
| False-positive rate                    |           3.00% |
| Random-attack detection rate           |             91% |
| Targeted-attack detection rate         |              3% |
| Model-consistent-attack detection rate |              3% |

The detector performed differently across attack scenarios. In particular, the recorded targeted and model-consistent attacks were often not detected by the residual detector. This is an important limitation, not a result to hide.

### Blockchain verification and performance

In the integrated experiment, changed payloads failed verification against previously registered clean references. An attacked payload registered first verified against its own registered hash, illustrating that a hash is an integrity reference, not a source of physical truth.

Recorded local Hardhat performance:

| Operation    | Median latency | P95 latency |
| ------------ | -------------: | ----------: |
| Submission   |      20.534 ms |   28.598 ms |
| Verification |       7.110 ms |   10.226 ms |

These latency figures were measured on a local development chain and should not be generalized to a production network.

### Output files

- `results/integrated_trials.csv` — trial-level integrated experiment data.
- `results/integrated_summary.csv` — integrated summary metrics.
- `results/integrated_residual_metrics.csv` — residual-detector metrics.
- `results/integrated_detection_comparison.png` — detection comparison plot.
- `results/phase2_trials.csv` and `results/phase2_summary.csv` — Phase 2 trial and summary data.
- `results/blockchain_benchmark.csv` and `results/blockchain_benchmark_summary.json` — blockchain benchmark results.

## Tests

Run the automated test suite:

```powershell
python -m pytest -q
```

The latest validation run reported:

```text
33 passed in 10.29s
```

Check the Python dependency environment:

```powershell
python -m pip check
```

The latest validation reported `No broken requirements found.`

These are the latest recorded results; rerun the commands after making code changes.

## Limitations and security considerations

1. **A hash does not prove physical truth.** It proves that a payload matches a registered fingerprint. It does not prove that the measurement was accurate when registered.
2. **Authorized sources can submit false data.** If a compromised or malicious authorized source registers a false measurement first, the registry can preserve that false payload's hash.
3. **Residual detection can miss stealthy attacks.** Model-consistent and carefully targeted attacks may evade the implemented residual detector.
4. **The test environment is synthetic.** Results come from the implemented simulated network and attack scenarios, not a field deployment.
5. **Hardhat is a development chain.** This prototype does not implement a production consortium network with independently operated validators and production consensus.
6. **Performance is environment-dependent.** Latency and gas figures from the local chain should not be treated as production performance estimates.
7. **The combined check has a defined threat model.** A hash mismatch can reveal a change relative to a trusted, previously registered reference. It cannot by itself identify who changed the data or whether the original source was trustworthy.

## Reproducibility notes

- Run commands from the project root.
- Keep the Hardhat node running for blockchain-dependent commands.
- Redeploy the contract after restarting the local Hardhat node.
- Preserve the generated CSV files and plots used in the final report.
- Record the Python, Node.js, Hardhat, and Solidity versions when producing a new set of results.
- Do not commit private keys, RPC credentials, or populated `.env` files.
- Treat the reported metrics as results from the recorded experiment configuration.

## Future work

Potential extensions include:

- Add sensor redundancy and physical plausibility checks.
- Investigate detection methods for targeted and model-consistent FDIA.
- Evaluate on larger or benchmark power-system networks.
- Test a multi-node permissioned blockchain with a documented consensus configuration.
- Evaluate behavior under sensor compromise, communication delays, and missing measurements.
- Add reproducible experiment configuration files and automated result validation.

## Conclusion

This prototype combines WLS-based state estimation, residual-based FDIA detection, and blockchain-backed measurement-integrity verification. The experiments illustrate that the methods address different aspects of the problem: residual analysis detects some measurement inconsistencies, while blockchain verification detects changes relative to a previously registered payload.

The results also show why the distinction matters: neither method alone guarantees that every measurement is physically valid. The current implementation is a research prototype that provides a reproducible starting point for further investigation.

## About

A research prototype for FDIA detection and measurement-integrity verification in simulated smart microgrids using Python, WLS state estimation, residual analysis, Solidity, and a local Hardhat blockchain.
