import { createClient } from "@supabase/supabase-js";
import { createServerClient } from "@supabase/ssr";
import type { SessionIdentity as ContractSessionIdentity } from "../use-cases/contracts";
import { forbidden, unauthorized } from "../http/errors";
import { createSupabaseServerClient } from "../../lib/supabase/server";

export type SessionIdentity = ContractSessionIdentity;

type UsuarioRow = {
  id: string;
  rol: string;
  cliente_id: string | null;
  activo: boolean;
};

const demoIdentity: SessionIdentity = {
  userId: "demo-user",
  rol: "cliente",
  clienteId: "demo-cliente"
};

function requireSupabaseConfig() {
  const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL;
  const supabaseKey = process.env.NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY;
  const serviceRoleKey = process.env.SUPABASE_SERVICE_ROLE_KEY;

  if (!supabaseUrl || !supabaseKey) {
    throw unauthorized("Supabase auth env vars are not configured");
  }

  return { supabaseUrl, supabaseKey, serviceRoleKey };
}

function parseCookieHeader(cookieHeader: string | null) {
  if (!cookieHeader) {
    return [];
  }

  return cookieHeader
    .split(";")
    .map((part) => part.trim())
    .filter(Boolean)
    .map((part) => {
      const index = part.indexOf("=");
      if (index === -1) {
        return null;
      }

      return {
        name: part.slice(0, index),
        value: decodeURIComponent(part.slice(index + 1))
      };
    })
    .filter((item): item is { name: string; value: string } => item !== null);
}

function resolveDemoIdentity(request: Request): SessionIdentity | null {
  if (request.headers.get("x-demo-mode") !== "1") {
    return null;
  }

  const rol = request.headers.get("x-demo-role")?.trim();
  if (rol !== "cliente" && rol !== "lider") {
    throw unauthorized("Invalid demo role");
  }

  return {
    userId: request.headers.get("x-demo-user-id")?.trim() || demoIdentity.userId,
    rol,
    clienteId: request.headers.get("x-demo-cliente-id")?.trim() || demoIdentity.clienteId
  };
}

async function resolveIdentityByUserId(userId: string): Promise<SessionIdentity> {
  const { supabaseUrl, supabaseKey, serviceRoleKey } = requireSupabaseConfig();

  if (!serviceRoleKey) {
    throw unauthorized("Supabase service role key is not configured");
  }

  const adminClient = createClient(supabaseUrl, serviceRoleKey, {
    auth: {
      autoRefreshToken: false,
      persistSession: false
    }
  });

  const { data, error } = await adminClient
    .from("usuario")
    .select("id, rol, cliente_id, activo")
    .eq("id", userId)
    .maybeSingle<UsuarioRow>();

  if (error) {
    throw unauthorized(error.message);
  }

  if (!data || !data.activo) {
    throw forbidden("Usuario no autorizado");
  }

  return {
    userId: data.id,
    rol: data.rol as SessionIdentity["rol"],
    clienteId: data.cliente_id
  };
}

export async function resolveIdentityFromRequest(request: Request): Promise<SessionIdentity> {
  const demo = resolveDemoIdentity(request);
  if (demo) {
    return demo;
  }

  const authorization = request.headers.get("authorization");

  if (authorization?.startsWith("Bearer ")) {
    const token = authorization.slice("Bearer ".length).trim();
    if (!token) {
      throw unauthorized("Missing bearer token");
    }

    const { supabaseUrl, supabaseKey } = requireSupabaseConfig();
    const supabase = createClient(supabaseUrl, supabaseKey, {
      auth: {
        autoRefreshToken: false,
        persistSession: false
      }
    });

    const { data, error } = await supabase.auth.getUser(token);
    if (error || !data.user) {
      throw unauthorized(error?.message ?? "Invalid session");
    }

    return resolveIdentityByUserId(data.user.id);
  }

  const { supabaseUrl, supabaseKey } = requireSupabaseConfig();
  const cookieStore = parseCookieHeader(request.headers.get("cookie"));
  const supabase = createServerClient(supabaseUrl, supabaseKey, {
    cookies: {
      getAll() {
        return cookieStore;
      },
      setAll() {
        // Route handlers only need to read the session.
      }
    }
  });

  const { data, error } = await supabase.auth.getUser();
  if (error || !data.user) {
    throw unauthorized(error?.message ?? "Missing authenticated session");
  }

  return resolveIdentityByUserId(data.user.id);
}

export async function resolveIdentityFromCurrentSession(): Promise<SessionIdentity | null> {
  try {
    const supabase = await createSupabaseServerClient();
    const { data, error } = await supabase.auth.getUser();

    if (error || !data.user) {
      return null;
    }

    return resolveIdentityByUserId(data.user.id);
  } catch {
    return null;
  }
}
