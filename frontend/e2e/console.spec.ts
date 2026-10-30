import { expect, test } from '@playwright/test'
import type { Page } from '@playwright/test'

async function login(page: Page, email: string) {
  await page.goto('/login')
  await page.getByRole('button', { name: new RegExp(email.replace('.', '\\.')) }).click()
  await page.locator('button[type="submit"]').click()
  await page.waitForURL((url) => !url.pathname.startsWith('/login'), { timeout: 20_000 })
  await expect(page.locator('.app-shell')).toBeVisible()
}

test('admin can review documents, users and chat history', async ({ page }) => {
  await login(page, 'admin@congty.vn')
  await expect(page).toHaveURL(/\/documents$/)
  await expect(page.getByRole('main').getByRole('heading', { name: 'Kho tài liệu' })).toBeVisible()
  await expect(page.getByText('Không kết nối được máy chủ.')).toHaveCount(0)

  await page.goto('/users')
  await expect(page.getByRole('main').getByRole('heading', { name: 'Người dùng' })).toBeVisible()
  await expect(page.locator('.ant-table-row')).toHaveCount(6)
  await expect(page.getByText('admin@congty.vn')).toBeVisible()

  await page.goto('/chat')
  await expect(page.getByText('Hỏi trợ lý về tri thức nội bộ')).toBeVisible()
  await page.getByRole('button', { name: 'Lịch sử' }).click()
  await expect(page.locator('.ant-drawer').getByText('Lịch sử trò chuyện')).toBeVisible()
})

test('manager lands on approvals and can see pending requests', async ({ page }) => {
  await login(page, 'manager@congty.vn')
  await expect(page).toHaveURL(/\/approvals$/)
  await expect(page.getByRole('main').getByRole('heading', { name: 'Phê duyệt' })).toBeVisible()
  await expect(page.locator('.ant-table-row')).toHaveCount(2)
  await expect(page.getByText('Lê Hoàng B')).toBeVisible()
  await expect(page.getByRole('button', { name: 'Duyệt' }).first()).toBeVisible()
})

test('IT support lands in the ticket queue with an AI suggestion', async ({ page }) => {
  await login(page, 'it@congty.vn')
  await expect(page).toHaveURL(/\/tickets\/queue$/)
  await expect(page.getByRole('main').getByRole('heading', { name: 'Hàng đợi IT' })).toBeVisible()
  await expect(page.getByText('Không nhận được email nội bộ').first()).toBeVisible()
  await expect(page.getByText('AI gợi ý xử lý')).toBeVisible()
  await expect(page.getByText('Đang mở')).toBeVisible()
})

test('employee lands on chat and cannot access admin screens', async ({ page }) => {
  await login(page, 'nva@congty.vn')
  await expect(page).toHaveURL(/\/chat$/)
  await expect(page.getByText('Hỏi trợ lý về tri thức nội bộ')).toBeVisible()

  await page.goto('/users')
  await expect(page).toHaveURL(/\/forbidden$/)
  await expect(
    page.getByText('Vai trò hiện tại của bạn không được phép mở trang này.', {
      exact: false,
    }),
  ).toBeVisible()
})

test('sidebar collapses into a drawer on tablet viewports', async ({ page }) => {
  await page.setViewportSize({ width: 1024, height: 800 })
  await login(page, 'nva@congty.vn')
  await page.getByRole('button', { name: 'Mở thanh điều hướng' }).click()
  await expect(page.locator('.context-sidebar')).toBeVisible()
  await page.locator('.context-close').click()
  await expect(page.locator('.context-sidebar')).toBeHidden()
})
