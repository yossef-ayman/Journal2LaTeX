import { lazy, Suspense } from "react";
import { createBrowserRouter, Navigate } from "react-router-dom";
import { MainLayout } from "@/layouts/MainLayout";

const HomePage = lazy(() => import("@/pages/Home"));
const UploadPage = lazy(() => import("@/pages/Upload"));
const ProcessingPage = lazy(() => import("@/pages/Processing"));
const ResultPage = lazy(() => import("@/pages/Result"));
const HistoryPage = lazy(() => import("@/pages/History"));
const SettingsPage = lazy(() => import("@/pages/Settings"));
const NotFoundPage = lazy(() => import("@/pages/NotFound"));

const Loader = () => (
  <div className="flex min-h-[400px] items-center justify-center">
    <div className="h-8 w-8 animate-spin rounded-full border-4 border-primary border-t-transparent" />
  </div>
);

function Lazy({ children }: { children: React.ReactNode }) {
  return <Suspense fallback={<Loader />}>{children}</Suspense>;
}

export const router = createBrowserRouter([
  {
    element: <MainLayout />,
    children: [
      { path: "/", element: <Lazy><HomePage /></Lazy> },
      { path: "/upload", element: <Lazy><UploadPage /></Lazy> },
      { path: "/processing/:jobId", element: <Lazy><ProcessingPage /></Lazy> },
      { path: "/result/:jobId", element: <Lazy><ResultPage /></Lazy> },
      { path: "/history", element: <Lazy><HistoryPage /></Lazy> },
      { path: "/settings", element: <Lazy><SettingsPage /></Lazy> },
      { path: "/404", element: <Lazy><NotFoundPage /></Lazy> },
      { path: "*", element: <Navigate to="/404" replace /> },
    ],
  },
]);
