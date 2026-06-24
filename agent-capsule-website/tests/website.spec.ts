import { expect, test } from "@playwright/test";

const requiredHeadings = [
  "Agent Capsule",
  "Agent teams need operational visibility without creating another data exposure path.",
  "A staged workflow for development, policy enforcement, and customer proof of concept.",
  "Data-flow visibility that fits pull request review.",
  "Share enough context to diagnose a run without exposing the run payloads.",
  "Prepare a private proof of concept from signed evidence.",
  "Shared semantics across the agent runtime stack.",
  "Local development does not require specialized hardware.",
  "Artifacts an enterprise reviewer can inspect before private evaluation data is used."
];

const forbiddenRawValues = [
  "claimant@example.com",
  "Neck pain reported after accident",
  "sig_test_value",
  "api-key"
];

test("renders the required product website sections", async ({ page }) => {
  await page.goto("/");
  for (const heading of requiredHeadings) {
    await expect(page.getByRole("heading", { name: heading })).toBeVisible();
  }
  await expect(page.getByText("Python", { exact: true })).toBeVisible();
  await expect(page.getByText("TypeScript", { exact: true })).toBeVisible();
  await expect(page.getByText("Java", { exact: true })).toBeVisible();
  await expect(page.getByText("Go", { exact: true })).toBeVisible();
  await expect(page.getByText("Rust", { exact: true })).toBeVisible();
});

test("first viewport shows product evidence and a hint of the next section", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByLabel("Agent Capsule product evidence visual")).toBeVisible();
  const evidenceBox = await page.getByLabel("Agent Capsule product evidence visual").boundingBox();
  expect(evidenceBox?.width).toBeGreaterThan(300);
  expect(evidenceBox?.height).toBeGreaterThan(180);
  const problemBox = await page.getByRole("heading", {
    name: "Agent teams need operational visibility without creating another data exposure path."
  }).boundingBox();
  expect(problemBox?.y ?? 9999).toBeLessThan(920);
});

test("visible UI avoids icons, emoji, and bold typography", async ({ page }) => {
  await page.goto("/");
  await expect(page.locator("main svg")).toHaveCount(0);
  await expect(page.locator("[data-lucide], .lucide")).toHaveCount(0);
  await expect(page.locator("strong, b")).toHaveCount(0);

  const bodyText = await page.locator("body").innerText();
  expect(bodyText).not.toMatch(/\p{Extended_Pictographic}/u);

  const heavyTextCount = await page.evaluate(() => {
    const nodes = Array.from(document.querySelectorAll("body *"));
    return nodes.filter((node) => {
      const element = node as HTMLElement;
      if (!element.innerText || element.offsetParent === null) {
        return false;
      }
      const weight = Number.parseInt(window.getComputedStyle(element).fontWeight, 10);
      return Number.isFinite(weight) && weight > 500;
    }).length;
  });
  expect(heavyTextCount).toBe(0);
});

test("copy avoids sensitive payloads and overstated guarantees", async ({ page }) => {
  await page.goto("/");
  const bodyText = await page.locator("body").innerText();
  for (const rawValue of forbiddenRawValues) {
    expect(bodyText).not.toContain(rawValue);
  }
  expect(bodyText).not.toContain("guarantees complete AI safety");
  expect(bodyText).not.toContain("eliminates prompt injection");
});

test("responsive layout avoids page-level horizontal overflow", async ({ page }) => {
  await page.goto("/");
  const metrics = await page.evaluate(() => ({
    scrollWidth: document.documentElement.scrollWidth,
    clientWidth: document.documentElement.clientWidth
  }));
  expect(metrics.scrollWidth).toBeLessThanOrEqual(metrics.clientWidth + 2);
});
