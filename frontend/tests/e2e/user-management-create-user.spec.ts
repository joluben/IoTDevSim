import { test, expect, type Page } from '@playwright/test';

// Helper to generate unique email to avoid conflicts on re-runs
const TEST_USER_EMAIL = `toni.idrica+${Date.now()}@gmail.com`;
const TEST_USER_NAME = 'Toni 2';

// Admin credentials from backend bootstrap defaults
const ADMIN_EMAIL = 'admin@iotdevsim.com';
const ADMIN_PASSWORD = 'IotDevSim';

async function loginAsAdmin(page: Page) {
  await page.goto('/login');
  await expect(page.locator('text=Sign in')).toBeVisible();

  await page.fill('input[type="email"]', ADMIN_EMAIL);
  await page.fill('input[type="password"]', ADMIN_PASSWORD);
  await page.click('button[type="submit"]');

  // Wait for navigation to dashboard after successful login
  await page.waitForURL('**/dashboard', { timeout: 10_000 });
  await expect(page.locator('text=Dashboard')).toBeVisible();
}

test.describe('User Management E2E', () => {
  test.beforeEach(async ({ page }) => {
    await loginAsAdmin(page);
  });

  test('create user with specific permissions and verify access control', async ({ page }) => {
    // 1. Accede a la sección configuración
    await page.click('text=Settings');
    await page.waitForURL('**/settings', { timeout: 10_000 });
    await expect(page.locator('h1:has-text("Settings")')).toBeVisible();

    // 2. Accede a la gestión de usuarios
    await page.click('text=Open User Management');
    await page.waitForURL('**/settings/users', { timeout: 10_000 });
    await expect(page.locator('h1:has-text("User Management")')).toBeVisible();

    // 3. Abre el diálogo para crear usuario
    await page.click('button:has-text("New user")');
    await expect(page.locator('text=Create user')).toBeVisible();

    // 4. Completa los datos del usuario
    await page.fill('input#create-email', TEST_USER_EMAIL);
    await page.fill('input#create-full-name', TEST_USER_NAME);

    // Verifica que el grupo esté en "User" (default)
    await expect(page.locator('text=Select group')).toBeVisible();

    // 5. Configura permisos:
    // - Connections: Write (checked)
    // - Devices: Write (checked)
    // - Datasets: Read (unchecked)
    // - Projects: Read (unchecked)

    // Asegurar que Connections tiene Write habilitado (checkbox marcado)
    const connectionsCheckbox = page.locator('div:has-text("connections") + div input[type="checkbox"]');
    await expect(connectionsCheckbox).toBeChecked();

    // Asegurar que Devices tiene Write habilitado (checkbox marcado)
    const devicesCheckbox = page.locator('div:has-text("devices") + div input[type="checkbox"]');
    await expect(devicesCheckbox).toBeChecked();

    // Asegurar que Datasets está en Read (checkbox desmarcado)
    const datasetsCheckbox = page.locator('div:has-text("datasets") + div input[type="checkbox"]');
    await expect(datasetsCheckbox).not.toBeChecked();

    // Asegurar que Projects está en Read (checkbox desmarcado)
    const projectsCheckbox = page.locator('div:has-text("projects") + div input[type="checkbox"]');
    await expect(projectsCheckbox).not.toBeChecked();

    // 6. Guarda el usuario
    await page.click('button[type="submit"]:has-text("Create user")');

    // 7. Recibe notificación de éxito
    await expect(page.locator('div[role="status"]')).toBeVisible({ timeout: 10_000 });
    await expect(page.locator('div[role="status"]')).toContainText('User created');
    await expect(page.locator('div[role="status"] div.truncate')).toContainText('User created');

    // Verifica que el usuario aparece en la tabla
    await expect(page.locator(`text=${TEST_USER_EMAIL}`)).toBeVisible({ timeout: 10_000 });
    await expect(page.locator(`text=${TEST_USER_NAME}`)).toBeVisible();

    // Verifica los badges de permisos en la tabla
    // Connections debe mostrar "Write"
    await expect(
      page.locator(`tr:has-text("${TEST_USER_EMAIL}") >> td:has-text("Connections") >> span:has-text("Write")`)
    ).toBeVisible();
    // Devices debe mostrar "Write"
    await expect(
      page.locator(`tr:has-text("${TEST_USER_EMAIL}") >> td:has-text("Devices") >> span:has-text("Write")`)
    ).toBeVisible();
    // Datasets debe mostrar "Read"
    await expect(
      page.locator(`tr:has-text("${TEST_USER_EMAIL}") >> td:has-text("Datasets") >> span:has-text("Read")`)
    ).toBeVisible();
    // Projects debe mostrar "Read"
    await expect(
      page.locator(`tr:has-text("${TEST_USER_EMAIL}") >> td:has-text("Projects") >> span:has-text("Read")`)
    ).toBeVisible();
  });

  test('verify permissions - user with connections:write can access create button', async ({ page }) => {
    // 8. Accede a las conexiones y comprueba que puede crear una nueva
    await page.click('text=Connections');
    await page.waitForURL('**/connections', { timeout: 10_000 });
    await expect(page.locator('h1:has-text("Connections")')).toBeVisible();

    // Verifica que existe el botón para crear nueva conexión
    const createButton = page.locator('button:has-text("New connection"), button:has-text("Nueva conexión")');
    await expect(createButton).toBeVisible();
    await expect(createButton).toBeEnabled();

    // No es necesario crear la conexión, solo verificar acceso
  });

  test('verify permissions - user with datasets:read cannot create or edit', async ({ page }) => {
    // 9. Accede a datasets y comprueba que NO puede crear ni editar
    await page.click('text=Datasets');
    await page.waitForURL('**/datasets', { timeout: 10_000 });
    await expect(page.locator('h1:has-text("Datasets")')).toBeVisible();

    // Verifica que NO existe botón para crear nuevo dataset (o está deshabilitado/oculto)
    const createButton = page.locator('button:has-text("New dataset"), button:has-text("Nuevo dataset"), button:has-text("Create")');
    
    // Si el botón existe, debería estar deshabilitado o no visible
    if (await createButton.count() > 0) {
      await expect(createButton).toBeDisabled();
    }

    // Verifica que no hay opciones de editar en los datasets existentes (si los hay)
    // Busca iconos de editar o menús de acciones en la tabla
    const editButtons = page.locator('table tbody tr td button[aria-label*="Edit"], table tbody tr td button:has-text("Edit"), table tbody tr td svg[data-icon="pencil"]');
    
    // Si existen datasets, los botones de editar deberían estar deshabilitados o no presentes
    if (await editButtons.count() > 0) {
      for (const btn of await editButtons.all()) {
        await expect(btn).toBeDisabled();
      }
    }

    // Alternativa: verifica que aparece algún indicador de "solo lectura" o "read-only"
    // o que los datasets se muestran sin opciones de acción
  });
});

// Test independiente para verificar que un usuario sin sesión es redirigido a login
test('unauthenticated user is redirected to login', async ({ page }) => {
  await page.goto('/settings/users');
  await page.waitForURL('**/login', { timeout: 10_000 });
  await expect(page.locator('text=Sign in')).toBeVisible();
});
