import { expect, test } from '@playwright/test'

async function login(page: Page, email: string) {
  await page.goto('/login')
  await page.getByRole('button', { name: new RegExp(email.replace('.', '\\.')) }).click()
  await page.locator('button[type="submit"]').click()
  await page.waitForURL((url) => !url.pathname.startsWith('/login'), { timeout: 20_000 })
  await expect(page.locator('.app-shell')).toBeVisible()
}

test('admin can delete documents with selection and verify sidebar consistency', async ({ page }) => {
  await login(page, 'admin@congty.vn')

  // 1. Kiểm tra sidebar trên trang Kho tài liệu
  await expect(page.locator('.context-sidebar__title')).toHaveText('Kho tài liệu')
  const groupLabels = page.locator('.context-group__label')
  const groupLabelCount = await groupLabels.count()
  // Kiểm tra mỗi group label không trùng với title (không duplicate)
  const title = await page.locator('.context-sidebar__title').textContent()
  const groupTexts = await groupLabels.allTextContents()
  for (const text of groupTexts) {
    expect(text.trim()).not.toBe(title?.trim())
  }

  // 2. Kiểm tra active item màu xanh đậm
  const activeItem = page.locator('.context-item--active')
  await expect(activeItem).toBeVisible()
  const activeStyles = await activeItem.evaluate((el) => {
    const style = window.getComputedStyle(el)
    return {
      backgroundColor: style.backgroundColor,
      color: style.color,
      fontWeight: style.fontWeight,
    }
  })
  // Màu xanh đậm #0B4F7A (RGB khoảng 11, 79, 122)
  const bgRgb = activeStyles.backgroundColor.match(/\d+/g)?.map(Number)
  expect(bgRgb).toBeTruthy()
  expect(bgRgb?.[0]).toBeLessThan(20) // R=11
  expect(bgRgb?.[1]).toBeGreaterThan(50) // G=79
  expect(bgRgb?.[2]).toBeGreaterThan(100) // B=122
  // Kiểm tra màu không phải light blue (#eaf3f9)
  expect(bgRgb?.[0]).not.toBe(234) // R
  expect(bgRgb?.[1]).not.toBe(243) // G
  expect(bgRgb?.[2]).not.toBe(249) // B
  // Kiểm tra text trắng
  const color = activeStyles.color
  expect(color).toBe('rgb(255, 255, 255)')

  // 3. Kiểm tra có thể chọn tài liệu (checkbox)
  const documentRows = page.locator('.ant-table-row').filter({ hasText: 'THESIS-001' })
  await expect(documentRows).toHaveCount(1)
  const firstCheckbox = documentRows.locator('.ant-checkbox-input')
  await firstCheckbox.check()

  // 4. Kiểm tra nút "Xóa đã chọn" hiển thị
  const deleteButton = page.locator('button:has-text("Xóa đã chọn")')
  await expect(deleteButton).toBeVisible()

  // 5. Xóa tài liệu và xác nhận
  await deleteButton.click()
  // Popconfirm xuất hiện
  const popconfirm = page.locator('.ant-popconfirm')
  await expect(popconfirm).toBeVisible()
  await popconfirm.locator('button:has-text("Xóa")').click()

  // 6. Kiểm tra message success
  await expect(page.locator('.ant-message-success')).toContainText('Đã xóa 1 tài liệu')

  // 7. Kiểm tra tài liệu đã biến mất
  await expect(documentRows).toHaveCount(0)

  // 8. Kiểm tra sidebar context item vẫn không duplicate
  await expect(page.locator('.context-sidebar__title')).toHaveText('Kho tài liệu')
  const newGroupLabels = page.locator('.context-group__label')
  const newGroupTexts = await newGroupLabels.allTextContents()
  for (const text of newGroupTexts) {
    expect(text.trim()).not.toBe('Kho tài liệu')
  }
})
