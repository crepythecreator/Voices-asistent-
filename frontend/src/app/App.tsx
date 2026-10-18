import { RouterProvider } from "react-router";

import { AuthProvider } from "@/features/auth";
import { router } from "./routes/router";

export function App() {
  return (
    <AuthProvider>
      <RouterProvider router={router} />
    </AuthProvider>
  );
}
