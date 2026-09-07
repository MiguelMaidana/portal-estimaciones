import { z } from "zod";
import { rolesUsuario } from "../domain";

export const rolUsuarioSchema = z.enum(rolesUsuario);

export const sesionUsuarioSchema = z.object({
  userId: z.string().uuid(),
  rol: rolUsuarioSchema,
  clienteId: z.string().uuid().nullable()
});
