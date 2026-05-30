import { BrowserRouter, Routes, Route } from "react-router-dom";
import Dashboard from "./pages/Dashboard";
import ReviewWorkspace from "./pages/ReviewWorkspace";

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Dashboard />} />
        <Route path="/review/:owner/:repo/:number" element={<ReviewWorkspace />} />
      </Routes>
    </BrowserRouter>
  );
}
