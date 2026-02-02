import { redirect } from "next/navigation";

// Placeholder: in production, check auth via backend (e.g. GET /api/auth/me or cookie)
export default function HomePage() {
  redirect("/login");
}
