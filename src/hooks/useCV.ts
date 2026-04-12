import { useState } from "react";

const CV_KEY = "backdoor_cv_text";

export function useCV() {
  const [cvText, setCVText] = useState<string>(() => localStorage.getItem(CV_KEY) ?? "");

  function storeCV(text: string) {
    localStorage.setItem(CV_KEY, text);
    setCVText(text);
  }

  function clearCV() {
    localStorage.removeItem(CV_KEY);
    setCVText("");
  }

  return { cvText, storeCV, clearCV, hasCV: cvText.length > 0 };
}
