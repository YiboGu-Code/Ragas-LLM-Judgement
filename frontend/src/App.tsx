import './App.css'
import { Navigate, RouterProvider, createBrowserRouter } from 'react-router-dom'
import Layout from './components/Layout'
import DatasetsUploadPage from './pages/DatasetsUploadPage'
import DatasetDetailPage from './pages/DatasetDetailPage'
import RunCreatePage from './pages/RunCreatePage'
import RunDetailPage from './pages/RunDetailPage'
import HealthPage from './pages/HealthPage'
import HelpPage from './pages/HelpPage'

function App() {
  const router = createBrowserRouter([
    {
      path: '/',
      element: <Layout />,
      children: [
        { index: true, element: <Navigate to="/datasets/upload" replace /> },
        { path: 'health', element: <HealthPage /> },
        { path: 'datasets/upload', element: <DatasetsUploadPage /> },
        { path: 'datasets/:datasetId', element: <DatasetDetailPage /> },
        { path: 'runs/create', element: <RunCreatePage /> },
        { path: 'runs/:runId', element: <RunDetailPage /> },
        { path: 'help', element: <HelpPage /> },
      ],
    },
  ])

  return <RouterProvider router={router} />
}

export default App
