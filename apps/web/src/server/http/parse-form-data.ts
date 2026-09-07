export async function parseMultipartFormData(request: Request) {
  const formData = await request.formData();
  const getText = (key: string) => {
    const value = formData.get(key);
    return typeof value === "string" ? value : "";
  };

  return {
    clienteId: getText("clienteId"),
    textoOriginal: getText("textoOriginal"),
    textoOcr: getText("textoOcr") || null,
    contieneContenidoOcr: getText("contieneContenidoOcr") === "true",
    periodo: getText("periodo"),
    aceptado: getText("aceptado") === "true",
    aprobado: getText("aprobado") === "true",
    imagenes: formData
      .getAll("imagenes")
      .filter((item): item is File => item instanceof File)
      .map((file) => ({ name: file.name, type: file.type, size: file.size }))
  };
}
