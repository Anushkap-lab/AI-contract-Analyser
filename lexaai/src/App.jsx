import { useAuth,AuthProvider} from "./hooks/useAuth.jsx"
import ProtectedRoute from "./components/ProtectedRoute"
import Topbar from "./components/topbar"
import UploadZone from "./components/Upload"
import Skeleton from "./components/structure"
import ResultsDashboard from "./components/dashboard"
import { useContractAnalysis } from "./hooks/ContractAnalysis"

function Dashboard() {
  const { analyse, loading, result, error } = useContractAnalysis()

  return (
    <div className="page">
      <Topbar />
      <UploadZone onFileSelect={analyse} loading={loading} hasResult={!!result} />
      {error && <div className="error-box">{error}</div>}
      {loading && <Skeleton />}
      {!loading && result && <ResultsDashboard result={result} />}
    </div>
  )
}

export default function App() {
  return (
    <AuthProvider>
      <ProtectedRoute>
        <Dashboard />
      </ProtectedRoute>
    </AuthProvider>
  )
}

