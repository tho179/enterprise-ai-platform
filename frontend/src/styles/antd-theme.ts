import type { ThemeConfig } from 'antd'

export const antdTheme: ThemeConfig = {
  token: {
    colorPrimary: '#0B4F7A',
    colorInfo: '#0B4F7A',
    colorSuccess: '#15803D',
    colorWarning: '#B45309',
    colorError: '#B91C1C',
    colorText: '#0F172A',
    colorTextSecondary: '#64748B',
    colorBorder: '#E2E8F0',
    colorBorderSecondary: '#EEF2F6',
    colorBgLayout: '#F6F8FA',
    colorBgContainer: '#FFFFFF',
    borderRadius: 8,
    borderRadiusLG: 10,
    controlHeight: 36,
    fontSize: 14,
    fontFamily: "'Be Vietnam Pro', 'Segoe UI', system-ui, -apple-system, sans-serif",
    boxShadowSecondary: '0 8px 24px rgb(15 23 42 / 12%)',
  },
  components: {
    Button: {
      primaryShadow: 'none',
      defaultShadow: 'none',
      fontWeight: 500,
    },
    Table: {
      headerBg: '#F8FAFC',
      headerColor: '#475569',
      headerSplitColor: '#E2E8F0',
      rowHoverBg: '#F8FAFC',
      cellPaddingBlock: 12,
      cellPaddingInline: 14,
      borderColor: '#EEF2F6',
    },
    Tabs: {
      horizontalItemGutter: 24,
      itemSelectedColor: '#0B4F7A',
      inkBarColor: '#0B4F7A',
    },
    Card: {
      paddingLG: 20,
      headerHeight: 48,
    },
    Menu: {
      darkItemBg: '#0B1F33',
      darkSubMenuItemBg: '#0B1F33',
      darkItemSelectedBg: '#122C45',
    },
    Input: {
      activeShadow: '0 0 0 2px rgb(11 79 122 / 12%)',
    },
    Select: {
      optionSelectedBg: '#EAF3F9',
    },
    Tag: {
      defaultBg: '#F1F5F9',
      defaultColor: '#475569',
    },
    Segmented: {
      itemSelectedBg: '#FFFFFF',
      trackBg: '#EEF2F6',
    },
    Steps: {
      colorPrimary: '#0B4F7A',
    },
  },
}
