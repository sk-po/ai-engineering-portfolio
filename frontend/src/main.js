import { formatLevel, searchRequirements } from "./asvs.js";

const form = document.querySelector("#search-form");
const queryInput = document.querySelector("#query");
const levelInput = document.querySelector("#level");
const submitButton = document.querySelector("#submit-button");
const status = document.querySelector("#search-status");
const results = document.querySelector("#results");
const resultSummary = document.querySelector("#result-summary");

function appendTextElement(parent, tagName, className, text) {
  const element = document.createElement(tagName);
  element.className = className;
  element.textContent = text;
  parent.append(element);
  return element;
}

function renderResults(payload) {
  results.replaceChildren();
  resultSummary.textContent = `${payload.results.length}件の関連要件`;

  if (payload.results.length === 0) {
    appendTextElement(
      results,
      "p",
      "empty-state",
      "関連する要件を見つけられませんでした。別の言葉で質問してください。",
    );
    return;
  }

  for (const item of payload.results) {
    const article = document.createElement("article");
    article.className = "result-card";

    const meta = document.createElement("div");
    meta.className = "result-meta";
    appendTextElement(meta, "span", "requirement-id", item.requirement_id);
    appendTextElement(meta, "span", "level-badge", formatLevel(item.level));
    article.append(meta);

    appendTextElement(article, "h3", "result-title", item.section_name_ja);
    appendTextElement(article, "p", "result-description", item.description_ja);

    const details = document.createElement("details");
    const summary = document.createElement("summary");
    summary.textContent = "英語原文と分類を確認";
    details.append(summary);
    appendTextElement(details, "p", "english-description", item.description_en);
    appendTextElement(
      details,
      "p",
      "source-path",
      `${item.chapter_id} ${item.chapter_name_en} / ${item.section_id} ${item.section_name_en}`,
    );
    article.append(details);
    results.append(article);
  }
}

async function submitSearch() {
  status.textContent = "検索しています…";
  status.classList.remove("error");
  submitButton.disabled = true;

  try {
    const payload = await searchRequirements({
      query: queryInput.value,
      level: Number(levelInput.value),
    });
    renderResults(payload);
    status.textContent = payload.translation_notice;
  } catch (error) {
    results.replaceChildren();
    resultSummary.textContent = "検索結果";
    status.textContent = error instanceof Error ? error.message : "検索に失敗しました。";
    status.classList.add("error");
  } finally {
    submitButton.disabled = false;
  }
}

form?.addEventListener("submit", (event) => {
  event.preventDefault();
  void submitSearch();
});

for (const exampleButton of document.querySelectorAll("[data-example]")) {
  exampleButton.addEventListener("click", () => {
    queryInput.value = exampleButton.dataset.example ?? "";
    queryInput.focus();
  });
}
