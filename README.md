# StudyTool: Offline AI-Driven Assessment & Intelligent Question Extraction

## Overview

StudyTool is a robust, fully offline, privacy-first desktop application designed to optimize university-level exam preparation. It acts as an intelligent virtual examiner, leveraging a custom probabilistic sampling algorithm, local Large Language Models (LLMs), and local Speech-to-Text (S2T) processing. The system dynamically adapts to the user's knowledge gaps, evaluates spoken answers, and provides rich, rendered feedback—all without requiring an active internet connection.

## Core Features

* **Adaptive Probabilistic Sampling:** A mathematically rigorous question extraction engine inspired by Reinforcement Learning and Simulated Annealing, ensuring optimal review cycles.
* **Local AI Tutor (Ollama Integration):** Asynchronous background fetching of answers via locally hosted LLMs (e.g., Gemma), rendered dynamically in a browser-based HTML environment to fully support Markdown and LaTeX rendering.
* **Hands-Free Vocal Assessment:** Integration of PyAudio and OpenAI's Whisper model (optimized for CPU execution) to capture spoken answers. The local LLM acts as a zero-shot evaluator, assigning a quantitative score to the transcription.
* **Asynchronous UI Architecture:** A multithreaded CustomTkinter GUI that prevents blocking during heavy local AI inference or audio processing.
* **Automated Cross-Platform Deployment:** Setup scripts (`.bat` and `.sh`) that handle virtual environment creation, dependency resolution, and Ollama model pulling automatically.

## Architecture & Design Patterns

The project architecture strictly enforces a separation of concerns, ensuring high maintainability and scalability.

* **Model-View-Controller (MVC) Principle:** The mathematical engine (`QuestionExtraction`) is completely decoupled from the presentation layer (`IntegratedStudyApp`), allowing headless testing and easy migration to other UI frameworks (e.g., Flask/FastAPI).
* **Asynchronous Processing & Callback Routing:** To manage heavy I/O operations (audio recording, Whisper inference, Ollama HTTP requests), the application heavily utilizes Python's `threading` module. UI updates are securely routed back to the main thread via the `.after()` method.
* **Singleton-like Caching (Memoization):** LLM responses are cached in a stateful dictionary during the session to prevent redundant API calls, allowing instant retrieval in the post-session review module.
* **Data Isolation:** User data (logs, question banks, weights) is strictly isolated within dynamically generated subdirectories (e.g., `materie/<subject>/`), ensuring a clean Git repository and secure local storage.

## Mathematical Model: Adaptive Sampling Engine

The core of the application is its intelligent question extraction algorithm, which calculates the probability distribution of the question pool based on past performance, difficulty, and frequency.

### 1. Base Logits Calculation

For each question $i$, the base priority logit $L_i$ is determined by the user-defined difficulty $D_i \in [1, 5]$ and the historical answer quality $Q_i \in [1, 5]$. A lower quality yields a higher logit:

$$
L_i = D_i \times (6.0 - Q_i)
$$

### 2. Starvation Boost

To prevent less frequently extracted questions from being ignored, a starvation ratio is computed relative to the most frequently answered question $M$. A boost factor $\beta$ (default $\beta = 0.2$) is applied:

$$
S_i = \frac{M - A_i}{M}
$$

$$
L'_i = L_i \times (1.0 + \beta \times S_i)
$$

*(Where $A_i$ is the number of times question $i$ has been answered).*

### 3. Temperature Decay (Simulated Annealing Concept)

To ensure the system focuses heavily on weak spots as the user progresses, the Softmax temperature $T$ decays exponentially based on the total number of answers submitted $N$. This shifts the distribution from nearly uniform (exploration) to highly deterministic (exploitation):

$$
T = \max(T_{min}, T_{init} \cdot e^{-\lambda N})
$$

*(With initial parameters $T_{init} = 25.0$, $T_{min} = 5.0$, and decay rate $\lambda = 0.01$).*

### 4. Normalized Probability Distribution & Masking

To prevent the same question from appearing consecutively, a FIFO recent-history buffer applies a probability mask $K$. The final probability $P_i$ of extracting question $i$ is calculated using a stabilized Softmax function:

$$
P_i = \frac{e^{(L'_i - \max(L')) / T} \times K_i}{\sum_{j} (e^{(L'_j - \max(L')) / T} \times K_j)}
$$

## Tech Stack & Libraries

* **Core Backend:** Python 3, `numpy` (vectorized probabilistic math), `matplotlib` (progress tracking and data visualization).
* **User Interface:** `customtkinter` (modern dark-mode GUI components).
* **LLM API Integration:** `requests` (interfacing with the local Ollama REST API over `localhost:11434`), `base64` (secure prompt passing to the browser renderer).
* **Speech-to-Text Pipeline:** `pyaudio` (hardware stream access), `whisper` (OpenAI's robust S2T model running dynamically in `fp16=False` mode to prevent CPU tensor overflows on PyTorch).

## Installation & Usage

The project includes automated bootstrapping scripts for both Windows and Unix systems.

**For Windows:**
Simply run `install.bat`. The script will verify Python, initialize a virtual environment, install dependencies, configure Ollama (via Winget if missing), and pull the configured LLM model. Run `StudyTool.bat` for daily usage.

**For Linux/macOS:**

```bash
chmod +x install.sh
./install.sh
# For daily usage:
./StudyTool.sh
```
