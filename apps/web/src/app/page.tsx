import { redirect } from "next/navigation";
import { resolveIdentityFromCurrentSession } from "../server/auth/resolve-identity";

export const dynamic = "force-dynamic";
export const revalidate = 0;

export default async function HomePage() {
  const identity = await resolveIdentityFromCurrentSession();

  if (!identity) {
    redirect("/login");
  }

  redirect(identity.rol === "lider" ? "/lider" : "/historias/nueva");
}
