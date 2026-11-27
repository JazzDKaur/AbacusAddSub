import streamlit as st

st.set_page_config(page_title="Abacus Practice", page_icon="🧮")
st.title("Abacus Practice")

st.iframe(
    r"""
<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<style>
  * { box-sizing: border-box; }
  body {
    margin: 0;
    padding: 4px;
    color: #18263b;
    font: 16px system-ui, sans-serif;
  }
  section {
    background: #f7f9ff;
    border: 1px solid #d4dff1;
    border-radius: 16px;
    padding: clamp(16px, 4vw, 28px);
  }
  .fields, .summary {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(145px, 1fr));
    gap: 14px;
  }
  label {
    display: block;
    font-weight: 650;
    margin-bottom: 6px;
  }
  select, input, button {
    font: inherit;
    padding: 10px 12px;
    border-radius: 8px;
  }
  select, input {
    width: 100%;
    border: 1px solid #8293ad;
    background: white;
    color: #18263b;
  }
  button {
    border: 0;
    background: #254db3;
    color: white;
    font-weight: 700;
    cursor: pointer;
  }
  :focus-visible {
    outline: 3px solid #507be0;
    outline-offset: 2px;
  }
  #play { text-align: center; }
  header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 10px;
  }
  #timer { font: bold 1.45rem ui-monospace, monospace; }
  #timer.urgent { color: #ac2035; }
  progress { width: 100%; accent-color: #254db3; }
  .problem {
    display: table;
    min-width: 5ch;
    margin: 24px auto;
    text-align: right;
    font: bold clamp(2.75rem, 10vw, 4rem)/1.15 ui-monospace, monospace;
  }
  #bottom {
    border-bottom: 3px solid currentColor;
    padding-bottom: 6px;
    white-space: pre;
  }
  form { max-width: 340px; margin: auto; }
  .entry { display: flex; gap: 8px; }
  .entry input { min-width: 0; text-align: center; }
  .hint { color: #435674; font-size: .9rem; }
  #error { color: #ac2035; min-height: 1.4em; margin: 6px 0; }
  h2 { margin-top: 0; }
  .summary { margin-bottom: 18px; }
  .summary div {
    background: #e7eeff;
    padding: 12px;
    border-radius: 8px;
  }
  .summary strong { display: block; font-size: 1.5rem; }
  #table-wrap { overflow: auto; max-height: 350px; }
  table { width: 100%; border-collapse: collapse; text-align: left; }
  th, td { padding: 8px; border-bottom: 1px solid #a7b7cb; }
  thead { position: sticky; top: 0; background: #e7eeff; }
  td:first-child { white-space: nowrap; }
  tr.correct { background: #d0f1d8; color: #123e25; }
  tr.wrong { background: #ffd9dc; color: #681b26; }
  #again { margin-top: 16px; }
</style>
</head>
<body>
<section id="setup">
  <div class="fields">
    <div>
      <label for="operation">Operation</label>
      <select id="operation">
        <option value="multiply">Multiplication</option>
        <option value="divide">Division</option>
      </select>
    </div>
    <div>
      <label for="digits">Digit combination</label>
      <select id="digits"></select>
    </div>
  </div>
  <p class="hint" id="instructions"></p>
  <button id="start" type="button">Start 2-minute set</button>
</section>

<section id="play" hidden>
  <header>
    <strong id="question-number"></strong>
    <span id="timer" role="timer"></span>
  </header>
  <progress id="progress" max="120" value="120"
            aria-label="Time remaining"></progress>

  <div class="problem" role="status" aria-atomic="true">
    <div id="top"></div>
    <div id="bottom"></div>
  </div>

  <form id="answer-form" novalidate>
    <label for="answer">Your answer</label>
    <div class="entry">
      <input id="answer" type="text" inputmode="numeric"
             autocomplete="off" maxlength="12">
      <button type="submit">Submit</button>
    </div>
    <p id="error" role="status"></p>
    <p class="hint">Press Enter to submit and see the next question.</p>
  </form>
</section>

<section id="results" hidden>
  <h2 id="result-title" tabindex="-1">Time’s up!</h2>
  <div class="summary">
    <div>Total questions submitted<strong id="total"></strong></div>
    <div>Correct questions<strong id="correct"></strong></div>
    <div>Score<strong id="score"></strong></div>
  </div>
  <p id="empty" hidden>No answers were submitted this set.</p>
  <div id="table-wrap" tabindex="0" role="region" aria-label="Answer review">
    <table aria-label="Practice results">
      <thead>
        <tr>
          <th scope="col">Question</th>
          <th scope="col">Correct answer</th>
          <th scope="col">Input answer</th>
          <th scope="col">Correct or wrong</th>
        </tr>
      </thead>
      <tbody id="rows"></tbody>
    </table>
  </div>
  <button id="again" type="button">Practice again</button>
</section>

<script>
  const get = (id) => document.getElementById(id);
  const operation = get("operation");
  const digits = get("digits");
  const answer = get("answer");
  const combinations = [[1, 1], [2, 1], [3, 1], [2, 2], [3, 2], [3, 3]];
  const durationSeconds = 120;

  let deadline = 0;
  let timerHandle;
  let questions = [];
  let questionIndex = 0;
  let submitted = [];
  let symbol;

  function updateOptions() {
    const previous = digits.value || "1,1";
    const division = operation.value === "divide";
    const operator = division ? "÷" : "×";

    digits.replaceChildren(...combinations.map(([first, second]) =>
      new Option(`${first}-digit ${operator} ${second}-digit`, `${first},${second}`)
    ));
    digits.value = previous;
    get("instructions").textContent = division
      ? "Divide the top number by the bottom number. All answers are whole numbers."
      : "Multiply the top number by the bottom number.";
  }

  function makeQuestions(division, firstDigits, secondDigits) {
    const firstMin = 10 ** (firstDigits - 1);
    const firstMax = 10 ** firstDigits - 1;
    const secondMin = 10 ** (secondDigits - 1);
    const secondMax = 10 ** secondDigits - 1;
    const pool = [];

    for (let b = secondMin; b <= secondMax; b++) {
      if (division) {
        const minQuotient = Math.ceil(firstMin / b);
        const maxQuotient = Math.floor(firstMax / b);

        for (let quotient = minQuotient; quotient <= maxQuotient; quotient++) {
          pool.push({ a: b * quotient, b, correct: quotient });
        }
      } else {
        for (let a = firstMin; a <= firstMax; a++) {
          pool.push({ a, b, correct: a * b });
        }
      }
    }
    return pool;
  }

  function showQuestion() {
    // Draw without replacement until the question pool is exhausted.
    const pick = questionIndex
      + Math.floor(Math.random() * (questions.length - questionIndex));

    [questions[questionIndex], questions[pick]] =
      [questions[pick], questions[questionIndex]];

    const { a, b } = questions[questionIndex];
    get("question-number").textContent = `Question ${submitted.length + 1}`;
    get("top").textContent = a;
    get("bottom").textContent = `${symbol} ${b}`;
    get("error").textContent = "";

    answer.value = "";
    answer.focus();
  }

  function showResults() {
    clearInterval(timerHandle);
    deadline = 0;

    const total = submitted.length;
    const correctCount = submitted.filter(
      (item) => item.entered === item.correct
    ).length;

    get("total").textContent = total;
    get("correct").textContent = correctCount;
    get("score").textContent = total
      ? `${(100 * correctCount / total).toFixed(1)}%`
      : "0%";

    const rows = get("rows");
    rows.replaceChildren();

    for (const { a, b, correct, entered, raw } of submitted) {
      const isCorrect = entered === correct;
      const row = rows.insertRow();
      row.className = isCorrect ? "correct" : "wrong";

      const values = [
        `${a} ${symbol} ${b}`,
        correct,
        raw,
        isCorrect ? "Correct" : "Wrong",
      ];

      for (const value of values) {
        row.insertCell().textContent = value;
      }
    }

    get("empty").hidden = total > 0;
    get("table-wrap").hidden = total === 0;
    get("play").hidden = true;
    get("results").hidden = false;
    get("result-title").focus();
  }

  function updateTimer() {
    if (!deadline) return;

    const remaining = Math.max(
      0, Math.ceil((deadline - performance.now()) / 1000)
    );
    const minutes = Math.floor(remaining / 60);
    const seconds = String(remaining % 60).padStart(2, "0");

    get("timer").textContent = `${minutes}:${seconds}`;
    get("timer").classList.toggle("urgent", remaining <= 15);
    get("progress").value = remaining;

    if (remaining === 0) showResults();
  }

  operation.addEventListener("change", updateOptions);

  get("start").addEventListener("click", () => {
    const division = operation.value === "divide";
    const [firstDigits, secondDigits] = digits.value.split(",").map(Number);

    symbol = division ? "÷" : "×";
    questions = makeQuestions(division, firstDigits, secondDigits);
    submitted = [];
    questionIndex = 0;

    get("setup").hidden = true;
    get("play").hidden = false;
    showQuestion();

    deadline = performance.now() + durationSeconds * 1000;
    updateTimer();
    timerHandle = setInterval(updateTimer, 100);
  });

  get("answer-form").addEventListener("submit", (event) => {
    event.preventDefault();
    if (!deadline) return;

    if (performance.now() >= deadline) {
      updateTimer();
      return;
    }

    const raw = answer.value.trim();
    if (!/^\d+$/.test(raw)) {
      get("error").textContent = "Enter a whole number before submitting.";
      answer.focus();
      return;
    }

    submitted.push({
      ...questions[questionIndex],
      entered: Number(raw),
      raw,
    });

    questionIndex = (questionIndex + 1) % questions.length;
    showQuestion();
  });

  document.addEventListener("visibilitychange", updateTimer);

  get("again").addEventListener("click", () => {
    get("results").hidden = true;
    get("setup").hidden = false;
    get("start").focus();
  });

  updateOptions();
</script>
</body>
</html>
"""
)