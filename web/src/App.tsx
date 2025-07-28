import { BrowserRouter as Router, Routes, Route } from 'react-router-dom'
import { Toaster } from 'react-hot-toast'
import Chat from '@/components/Chat'
import KnowledgeBase from '@/pages/KnowledgeBase'

function App() {
  return (
    <>
      <Router>
        <Routes>
          <Route path="/" element={<Chat />} />
          <Route path="/knowledge" element={<KnowledgeBase />} />
        </Routes>
      </Router>
      <Toaster 
        position="top-center"
        toastOptions={{
          duration: 3000,
          style: {
            background: '#363636',
            color: '#fff',
          },
          success: {
            duration: 2000,
            iconTheme: {
              primary: '#4ade80',
              secondary: '#fff',
            },
          },
          error: {
            duration: 4000,
            iconTheme: {
              primary: '#ef4444',
              secondary: '#fff',
            },
          },
        }}
      />
    </>
  )
}

export default App
