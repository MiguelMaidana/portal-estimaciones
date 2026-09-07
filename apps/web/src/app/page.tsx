import { redirect } from "next/navigation";
import { resolveIdentityFromCurrentSession } from "../server/auth/resolve-identity";

export default async function HomePage() {
  const identity = await resolveIdentityFromCurrentSession();

  if (!identity) {
    redirect("/login");
  }

  redirect(identity.rol === "lider" ? "/lider" : "/historias/nueva");
}
