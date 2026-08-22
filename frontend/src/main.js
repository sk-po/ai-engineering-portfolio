import { createGreeting } from "./greeting.js";

const greetingElement = document.querySelector("#greeting");

if (greetingElement) {
  greetingElement.textContent = createGreeting("HelloWorld");
}
