
// Copy Console Log to Clipboard
const copyLogToClipboard = (): void => {
  const outputDiv = document.getElementById("output");
  if (!outputDiv) return;

  // Get text content (strip HTML tags)
  // innerText preserves newlines better than textContent for visual layout
  const text = outputDiv.innerText;

  if (!text) {
    showNotification("Log is empty", "info", 2000);
    return;
  }

  // Use navigator.clipboard if available (requires secure context)
  if (navigator.clipboard && navigator.clipboard.writeText) {
    navigator.clipboard.writeText(text).then(() => {
      showNotification("Log copied to clipboard", "success", 2000);
    }).catch((err) => {
      console.error("Failed to copy log via navigator.clipboard:", err);
      // Fallback
      fallbackCopyText(text);
    });
  } else {
    fallbackCopyText(text);
  }
};

const fallbackCopyText = (text: string): void => {
  try {
    const textArea = document.createElement("textarea");
    textArea.value = text;

    // Ensure it's not visible but part of DOM
    textArea.style.position = "fixed";
    textArea.style.left = "-9999px";
    textArea.style.top = "0";
    document.body.appendChild(textArea);

    textArea.focus();
    textArea.select();

    const successful = document.execCommand('copy');
    document.body.removeChild(textArea);

    if (successful) {
      showNotification("Log copied to clipboard", "success", 2000);
    } else {
      showNotification("Failed to copy log", "error");
    }
  } catch (err) {
    console.error("Fallback copy failed:", err);
    showNotification("Failed to copy log", "error");
  }
};
