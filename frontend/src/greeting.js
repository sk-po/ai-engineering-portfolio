export function createGreeting(name = "World") {
  const normalizedName = name.trim() || "World";
  return `Hello, ${normalizedName}!`;
}
