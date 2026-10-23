import { createBrowserRouter, Navigate } from "react-router";

import { AssistantPage } from "@/pages/assistant";
import { LoginPage } from "@/pages/login";
import { RegisterPage } from "@/pages/register";
import { SettingsPage } from "@/pages/settings";
import { routes } from "@/shared/config";
import { GuestRoute, ProtectedRoute } from "./guards";

export const router = createBrowserRouter([
  {
    element: <GuestRoute />,
    children: [
      { path: routes.login, element: <LoginPage /> },
      { path: routes.register, element: <RegisterPage /> },
    ],
  },
  {
    element: <ProtectedRoute />,
    children: [
      { path: routes.home, element: <AssistantPage /> },
      { path: routes.settings, element: <SettingsPage /> },
    ],
  },
  { path: "*", element: <Navigate to={routes.home} replace /> },
]);
