import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import '@fontsource/be-vietnam-pro/400.css'
import '@fontsource/be-vietnam-pro/500.css'
import '@fontsource/be-vietnam-pro/600.css'
import '@fontsource/be-vietnam-pro/700.css'
import 'antd/dist/reset.css'
import '@/styles/global.css'
import App from '@/App'
import { DEMO_MODE } from '@/lib/constants'

async function enableMocking(): Promise<void> {
  if (!DEMO_MODE) return
  const { worker } = await import('@/mocks/browser')
  await worker.start({
    onUnhandledFrame: 'bypass',
    serviceWorker: { url: '/mockServiceWorker.js' },
  })
}

void enableMocking().then(() => {
  const container = document.getElementById('root')
  if (!container) throw new Error('Missing #root element')
  createRoot(container).render(
    <StrictMode>
      <App />
    </StrictMode>,
  )
})
