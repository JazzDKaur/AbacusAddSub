import random
import re
import time

import pandas as pd
import streamlit as st


SET_SIZE = 10


def generate_question(digits, rows, mixed):
    """Generate a question with a positive first number and nonnegative totals."""
    minimum = 10 ** (digits - 1)
    maximum = 10 ** digits - 1
    operands = [random.randint(minimum, maximum)]
    total = operands[0]

    signs = [1] * (rows - 1)
    if mixed:
        signs = [random.choice((1, -1)) for _ in signs]
        signs[0] = -1
        if rows >= 3:
            signs[1] = 1
            if random.choice((True, False)):
                signs[0], signs[1] = signs[1], signs[0]

    for sign in signs:
        if sign == -1 and total >= minimum:
            operand = -random.randint(minimum, min(total, maximum))
        else:
            operand = random.randint(minimum, maximum)

        operands.append(operand)
        total += operand

    return operands, total


def highlight_result(row):
    if row["Result"] == "Correct":
        style = "background-color: #dcfce7; color: #14532d"
    else:
        style = "background-color: #fee2e2; color: #7f1d1d"

    return [style] * len(row)


def display_results(questions, answers, elapsed_seconds):
    results = []
    for index, ((operands, correct_answer), answer) in enumerate(
        zip(questions, answers), start=1
    ):
        expression = str(operands[0])
        for operand in operands[1:]:
            sign = "+" if operand > 0 else "−"
            expression += f" {sign} {abs(operand)}"

        results.append({
            "#": index,
            "Question": expression,
            "Correct answer": correct_answer,
            "Your answer": answer,
            "Result": "Correct" if answer == correct_answer else "Wrong",
        })

    correct = sum(result["Result"] == "Correct" for result in results)
    time_taken = "Unavailable"
    if elapsed_seconds is not None:
        minutes, seconds = divmod(elapsed_seconds, 60)
        time_taken = f"{minutes}:{seconds:02d}"

    st.subheader("Your results")
    total_column, correct_column, score_column = st.columns(3)
    total_column.metric("Total questions", len(questions))
    correct_column.metric("Total correct", correct)
    score_column.metric("Total score", f"{correct} / {len(questions)}")
    st.metric("Time taken", time_taken)

    results_df = pd.DataFrame(results).set_index("#")
    styled_results = results_df.style.apply(highlight_result, axis=1)
    st.table(styled_results)


def focus_answer_box(answer_key):
    # A fresh script request reruns autofocus after a validation error too.
    focus_id = time.monotonic_ns()
    st.html(
        f"""
        <script data-focus-request="{focus_id}">
        (() => {{
            const deadline = performance.now() + 2000;

            function focusAnswer() {{
                const input = document.querySelector(".st-key-{answer_key} input");
                if (input) {{
                    input.focus({{preventScroll: true}});
                }} else if (performance.now() < deadline) {{
                    requestAnimationFrame(focusAnswer);
                }}
            }}

            requestAnimationFrame(focusAnswer);
        }})();
        </script>
        """,
        unsafe_allow_javascript=True,
    )


def main():
    st.set_page_config(page_title="Abacus Practice", page_icon="🧮")
    st.title("🧮 Abacus Practice")

    if "questions" not in st.session_state:
        st.caption("Choose your settings and practise 10 questions at a time.")

        with st.form("settings"):
            digit_column, row_column = st.columns(2)
            digits = digit_column.selectbox(
                "Digits per number",
                (1, 2, 3),
                format_func=lambda number: f"{number}-digit",
            )
            rows = row_column.number_input(
                "Rows per question",
                min_value=2,
                max_value=20,
                value=3,
                step=1,
            )
            mode = st.radio(
                "Operations",
                ("Addition and subtraction", "Addition only"),
            )

            if st.form_submit_button("Start practice", type="primary"):
                mixed = mode == "Addition and subtraction"
                st.session_state.questions = [
                    generate_question(digits, rows, mixed)
                    for _ in range(SET_SIZE)
                ]
                st.session_state.answers = []
                st.session_state.elapsed_seconds = None
                st.session_state.started_at = time.monotonic()
                st.rerun()

        return

    questions = st.session_state.questions
    answers = st.session_state.answers
    index = len(answers)

    if index == len(questions):
        display_results(
            questions,
            answers,
            st.session_state.get("elapsed_seconds"),
        )

        if st.button("Start a new set", type="primary"):
            for key in ("questions", "answers", "started_at", "elapsed_seconds"):
                st.session_state.pop(key, None)
            st.rerun()

        return

    st.progress(index / len(questions))
    st.subheader(f"Question {index + 1} of {len(questions)}")

    operands, _ = questions[index]
    lines = [f"  {operands[0]:>3}"]
    for operand in operands[1:]:
        sign = "+" if operand > 0 else "−"
        lines.append(f"{sign} {abs(operand):>3}")

    stack = "\n".join([*lines, "─────"])
    st.html(
        '<pre style="font: 600 1.8rem/1.2 monospace; margin: 0; '
        f'white-space: pre;">{stack}</pre>'
    )

    answer_key = f"answer_{index}"
    with st.form(f"question_{index}"):
        answer = st.text_input("Your answer", key=answer_key, max_chars=8)
        label = "Finish set" if index == len(questions) - 1 else "Next question"
        submitted = st.form_submit_button(label, type="primary")

    if submitted:
        cleaned_answer = answer.strip()
        if not re.fullmatch(r"[+-]?[0-9]+", cleaned_answer):
            st.error("Enter a whole number to continue.")
        else:
            answers.append(int(cleaned_answer))
            started_at = st.session_state.get("started_at")
            if len(answers) == len(questions) and started_at is not None:
                st.session_state.elapsed_seconds = int(
                    time.monotonic() - started_at
                )
            st.rerun()

    focus_answer_box(answer_key)


if __name__ == "__main__":
    main()