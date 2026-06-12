import { expect, test, type Route } from "@playwright/test";

const accessToken = "test-access-token";
const refreshToken = "test-refresh-token";
const userId = "11111111-1111-4111-8111-111111111111";
const configId = "22222222-2222-4222-8222-222222222222";
const createdAt = "2026-06-11T09:00:00Z";

test("signup confirmation onboarding and dashboard notifications", async ({
  page,
}) => {
  await page.route("**/api/v1/**", routeDjangoApi);

  await page.goto("/signup");
  await page.getByLabel("Username").fill("Diana");
  await page.getByLabel("Email").fill("diana@example.com");
  await page.getByLabel("Password", { exact: true }).fill("password123");
  await page.getByLabel("Confirm password").fill("password123");
  await page.getByRole("button", { name: "Sign up" }).click();
  await expect(
    page.getByRole("heading", { name: "Check your inbox" }),
  ).toBeVisible();

  await page.goto("/confirm-email?token=confirm-token");
  await expect(
    page.getByRole("heading", { name: "Tell us about yourself" }),
  ).toBeVisible();
  await page.getByLabel("Name").fill("Diana Agent");
  await page.getByRole("button", { name: "Next", exact: true }).click();

  await expect(
    page.getByRole("heading", { name: "Professional summary" }),
  ).toBeVisible();
  await page.getByLabel("Summary").fill("Product-minded backend engineer.");
  await page.getByRole("button", { name: "Next", exact: true }).click();

  await page.getByLabel("Domain").fill("Software platforms");
  await page.getByRole("button", { name: "Next", exact: true }).click();
  await page.getByLabel("Years of experience").fill("6");
  await page.getByRole("button", { name: "Next", exact: true }).click();
  await page
    .getByLabel("Skills (comma-separated)")
    .fill("Python, Django, Svelte");
  await page.getByRole("button", { name: "Next", exact: true }).click();

  await page.setInputFiles('input[type="file"]', {
    buffer: Buffer.from(
      "%PDF-1.4\n1 0 obj\n<<>>\nendobj\ntrailer\n<<>>\n%%EOF",
    ),
    mimeType: "application/pdf",
    name: "diana-cv.pdf",
  });
  await page.getByRole("button", { name: "Next", exact: true }).click();

  await page.getByLabel("Config name (optional)").fill("Platform roles");
  await page
    .getByLabel("Keywords (comma-separated)")
    .fill("Django, platform engineer");
  await page.getByLabel("Location").fill("Remote");
  await page.getByLabel("Remote only").check();
  await page.getByRole("button", { name: "Finish setup" }).click();

  await expect(page).toHaveURL(/\/dashboard$/);
  await expect(page.getByRole("heading", { name: "Diana" })).toBeVisible();
  await expect(page.getByRole("main").getByText("Search queued")).toBeVisible();
  await expect(page.getByText("1").first()).toBeVisible();
});

async function routeDjangoApi(route: Route): Promise<void> {
  const request = route.request();
  const url = new URL(request.url());
  const path = url.pathname;
  const method = request.method();

  if (method === "POST" && path === "/api/v1/auth/signup") {
    await fulfill(route, {
      user_id: userId,
      email: "diana@example.com",
      confirmation_required: true,
      confirmation_sent: true,
    });
    return;
  }
  if (method === "POST" && path === "/api/v1/auth/confirm-email") {
    await fulfill(route, {
      confirmed_at: createdAt,
      email: "diana@example.com",
      token: tokenData(),
      user_id: userId,
    });
    return;
  }
  if (method === "GET" && path === "/api/v1/auth/me") {
    await fulfill(route, userAccount());
    return;
  }
  if (method === "GET" && path === "/api/v1/profile") {
    await fulfill(route, profileResponse());
    return;
  }
  if (method === "PUT" && path === "/api/v1/profile") {
    await fulfill(route, profileResponse());
    return;
  }
  if (method === "POST" && path === "/api/v1/profile/cv") {
    await fulfill(route, {
      has_master_cv: true,
      storage_path: "profiles/diana-cv.pdf",
      text_chars: 24,
    });
    return;
  }
  if (method === "GET" && path === "/api/v1/job-configs/schedule-presets") {
    await fulfill(route, [
      { fetch_schedule_cron: "0 6 * * *", id: "daily", label: "Daily" },
      { fetch_schedule_cron: "0 6 * * 1", id: "weekly", label: "Weekly" },
    ]);
    return;
  }
  if (method === "GET" && path === "/api/v1/job-configs") {
    await fulfill(route, [jobConfigResponse()]);
    return;
  }
  if (method === "POST" && path === "/api/v1/job-configs") {
    await fulfill(route, jobConfigResponse());
    return;
  }
  if (method === "POST" && path === `/api/v1/job-configs/${configId}/run`) {
    await fulfill(route, { task_id: "task-1" });
    return;
  }
  if (method === "GET" && path === "/api/v1/notifications") {
    await fulfill(route, {
      items: [
        {
          body: "Your first job search is queued.",
          created_at: createdAt,
          event_type: "job_config_run_queued",
          id: "33333333-3333-4333-8333-333333333333",
          payload: { config_id: configId },
          read_at: null,
          title: "Search queued",
        },
      ],
      unread_count: 1,
    });
    return;
  }

  await route.fulfill({
    body: JSON.stringify({
      data: null,
      error: { code: "not_found", message: path },
      meta: null,
    }),
    contentType: "application/json",
    status: 404,
  });
}

async function fulfill<TData>(
  route: Route,
  data: TData,
  status = 200,
): Promise<void> {
  await route.fulfill({
    body: JSON.stringify({ data, error: null, meta: null }),
    contentType: "application/json",
    status,
  });
}

function tokenData() {
  return {
    access_token: accessToken,
    expires_in: 900,
    refresh_token: refreshToken,
    token_type: "bearer",
    user_id: userId,
  };
}

function userAccount() {
  return {
    email: "diana@example.com",
    email_confirmed_at: createdAt,
    username: "Diana",
    id: userId,
    subscription_tier: "free",
  };
}

function profileResponse() {
  return {
    created_at: createdAt,
    domain: "Software platforms",
    experience_years: 6,
    full_name: "Diana Agent",
    has_master_cv: true,
    id: "44444444-4444-4444-8444-444444444444",
    linkedin_url: null,
    professional_summary: "Product-minded backend engineer.",
    skills: ["Python", "Django", "Svelte"],
    updated_at: createdAt,
    user_id: userId,
    values_statement: null,
  };
}

function jobConfigResponse() {
  return {
    created_at: createdAt,
    employment_types: [],
    fetch_schedule_cron: "0 6 * * *",
    id: configId,
    is_active: true,
    keywords: ["Django", "platform engineer"],
    location: "Remote",
    name: "Platform roles",
    remote_only: true,
    salary_max: null,
    salary_min: null,
    updated_at: createdAt,
    user_id: userId,
  };
}
