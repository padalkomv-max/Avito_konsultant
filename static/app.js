const MAX_FILES = 10;
const MAX_FILE_BYTES = 5 * 1024 * 1024;

const CRITERIA_LABELS = {
  headline: "Заголовок",
  price: "Цена",
  description: "Описание",
  structure: "Структура",
  offer_clarity: "Ясность предложения (что продаётся)",
  benefit: "Выгода для клиента",
  trust: "Доверие",
  photos: "Фото",
  audience_fit: "Соответствие аудитории",
};

function formatHttpDetail(detail) {
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail)) {
    return detail
      .map((item) => {
        if (typeof item === "string") return item;
        if (item && typeof item.msg === "string") return item.msg;
        return JSON.stringify(item);
      })
      .join(" ");
  }
  return "Произошла ошибка. Попробуйте ещё раз.";
}

function validateFiles(fileInput) {
  const files = fileInput.files;
  if (!files || files.length === 0) {
    return "Выберите хотя бы один файл со скриншотом.";
  }
  if (files.length > MAX_FILES) {
    return `Можно загрузить не более ${MAX_FILES} файлов.`;
  }
  for (let i = 0; i < files.length; i++) {
    if (files[i].size > MAX_FILE_BYTES) {
      return `Файл «${files[i].name}» больше 5 МБ. Выберите другой файл или сожмите изображение.`;
    }
  }
  return null;
}

function clearResult() {
  document.getElementById("result-area").classList.add("hidden");
}

function showError(text) {
  const el = document.getElementById("client-error");
  el.textContent = text;
  el.hidden = false;
}

function hideError() {
  const el = document.getElementById("client-error");
  el.textContent = "";
  el.hidden = true;
}

function formatOverallScore(score) {
  const n = typeof score === "number" ? score : parseInt(String(score ?? ""), 10);
  if (!Number.isFinite(n)) return "— / 10";
  return `${n} / 10`;
}

function fillResults(data) {
  document.getElementById("score-overall").textContent = formatOverallScore(data.score_overall);
  document.getElementById("score-label").textContent = data.score_label || "";

  const criteriaList = document.getElementById("criteria-list");
  criteriaList.innerHTML = "";
  const scores = data.scores_by_criteria || {};
  const order = [
    "headline",
    "price",
    "description",
    "structure",
    "offer_clarity",
    "benefit",
    "trust",
    "photos",
    "audience_fit",
  ];
  order.forEach((key) => {
    const val = scores[key];
    if (val === undefined || val === null) return;
    const li = document.createElement("li");
    li.innerHTML = `<span class="criteria-name">${CRITERIA_LABELS[key] || key}</span><span class="criteria-score">${val} / 10</span>`;
    criteriaList.appendChild(li);
  });

  function fillList(id, items) {
    const ul = document.getElementById(id);
    ul.innerHTML = "";
    (items || []).forEach((t) => {
      const li = document.createElement("li");
      li.textContent = t;
      ul.appendChild(li);
    });
  }

  fillList("list-strengths", data.strengths);
  fillList("list-weaknesses", data.weaknesses);
  fillList("list-recommendations", data.recommendations);

  document.getElementById("improved-text").textContent = data.improved_text_short || "";
  document.getElementById("final-summary").textContent = data.final_summary || "";
  document.getElementById("final-offer").textContent = data.final_offer || "";

  document.getElementById("result-area").classList.remove("hidden");
  document.getElementById("result-area").scrollIntoView({ behavior: "smooth", block: "start" });
}

document.getElementById("analyze-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  hideError();
  clearResult();

  const form = e.target;
  const fileInput = form.querySelector('input[type="file"]');
  const clientErr = validateFiles(fileInput);
  if (clientErr) {
    showError(clientErr);
    return;
  }

  const btn = document.getElementById("submit-btn");
  btn.disabled = true;

  const fd = new FormData();
  for (let i = 0; i < fileInput.files.length; i++) {
    fd.append("files", fileInput.files[i]);
  }
  const niche = form.niche.value.trim();
  const audience = form.audience.value.trim();
  const comment = form.comment.value.trim();
  if (niche) fd.append("niche", niche);
  if (audience) fd.append("audience", audience);
  if (comment) fd.append("comment", comment);

  try {
    const res = await fetch("/api/analyze", {
      method: "POST",
      body: fd,
    });
    const data = await res.json().catch(() => ({}));

    if (!res.ok) {
      showError(formatHttpDetail(data.detail) || "Запрос не выполнен.");
      return;
    }

    fillResults(data);
  } catch {
    showError("Не удалось связаться с сервером. Проверьте соединение и попробуйте снова.");
  } finally {
    btn.disabled = false;
  }
});
