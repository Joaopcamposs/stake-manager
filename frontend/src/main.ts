import "./style.css";

// Page-specific module loading based on body data attribute or URL
const page = document.body.dataset.page || detectPage();

function detectPage(): string {
  const path = window.location.pathname;
  if (path.includes("dashboard")) return "dashboard";
  return "home";
}

async function loadPageModule(pageName: string) {
  switch (pageName) {
    case "home":
      await import("./home");
      break;
    case "dashboard":
      await import("./dashboard");
      break;
  }
}

document.addEventListener("DOMContentLoaded", () => {
  loadPageModule(page);
});
