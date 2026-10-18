import { createBrowserRouter, Navigate } from "react-router";

import { AssistantPage } from "@/pages/assistant";
import { LoginPage } from "@/pages/login";
import { routes } from "@/shared/config";
import { GuestRoute, ProtectedRoute } from "./guards";

export const router = createBrowserRouter([
  {
    element: <GuestRoute />,
    children: [{ path: routes.login, element: <LoginPage /> }],
  },
  {
    element: <ProtectedRoute />,
    children: [{ path: routes.home, element: <AssistantPage /> }],
  },
  { path: "*", element: <Navigate to={routes.home} replace /> },
]);
