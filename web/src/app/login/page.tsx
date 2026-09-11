import { Suspense } from "react";
import LoginPage from "./page-client";

export default function Page() {
  return (
    <Suspense fallback={<div className="flex min-h-svh items-center justify-center">Carregando...</div>}>
      <LoginPage />
    </Suspense>
  );
}
