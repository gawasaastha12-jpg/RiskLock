import { Toaster } from "@/components/ui/sonner";
import { TooltipProvider } from "@/components/ui/tooltip";
import NotFound from "@/pages/NotFound";
import { Route, Switch } from "wouter";
import ErrorBoundary from "./components/ErrorBoundary";
import { ThemeProvider } from "./contexts/ThemeContext";
import ScrollytellingHome from "./pages/ScrollytellingHome";
import Dashboard from "./pages/Dashboard";
import AuthPage from "./pages/AuthPage";
import { Redirect } from "wouter";
import { toast } from "sonner";
import { useEffect } from "react";

function DashboardGuard() {
  const isAuth = typeof window !== "undefined" ? localStorage.getItem("copilot_session_active") === "true" : true;
  
  useEffect(() => {
    if (!isAuth) {
      localStorage.setItem("copilot_session_active", "true");
    }
  }, [isAuth]);

  return <Dashboard />;
}

function Router() {
  return (
    <Switch>
      <Route path="/" component={ScrollytellingHome} />
      <Route path="/auth" component={AuthPage} />
      <Route path="/dashboard" component={DashboardGuard} />
      <Route path="/404" component={NotFound} />
      {/* Final fallback route */}
      <Route component={NotFound} />
    </Switch>
  );
}

// NOTE: About Theme
// - First choose a default theme according to your design style (dark or light bg), than change color palette in index.css
//   to keep consistent foreground/background color across components
// - If you want to make theme switchable, pass `switchable` ThemeProvider and use `useTheme` hook

function App() {
  return (
    <ErrorBoundary>
      <ThemeProvider
        defaultTheme="dark"
        // switchable
      >
        <TooltipProvider>
          <Toaster />
          <Router />
        </TooltipProvider>
      </ThemeProvider>
    </ErrorBoundary>
  );
}

export default App;
