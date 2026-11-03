/* Portable Jaal: Escape leaves viewport-focus mode through the normal
 * Dash toggle button. No internal vis-network state or graph data is touched.
 * The listener is inert for normal views and non-browser test runners. */
(function (root) {
  "use strict";
  if (!root || typeof root.addEventListener !== "function" ||
      !root.document) return;
  root.addEventListener("keydown", function (event) {
    if (event.key !== "Escape" || event.defaultPrevented) return;
    const shell = root.document.getElementById("jaal-viewer-root");
    if (!shell || !shell.classList.contains("jaal-focus-mode")) return;
    const button = root.document.getElementById("jaal-focus-toggle");
    if (!button) return;
    event.preventDefault();
    button.click();
  }, true);
})(typeof window !== "undefined" ? window : null);
