type ValidationIssue = {loc?: (string | number)[];type?:string;msg?:string;ctx?:{min_length?:number;max_length?:number}};
const fieldNames:Record<string,string> = {
  password:'senha', new_password:'nova senha', current_password:'senha atual',
  email:'e-mail', name:'nome', token:'link de verificação', email_interval:'frequência', password_interval:'frequência',
};
export function errorMessage(data: unknown, status: number): string {
  if (data && typeof data === 'object' && 'detail' in data) {
    const detail = (data as {detail:unknown}).detail;
    if (typeof detail === 'string') return detail;
    if (Array.isArray(detail)) {
      const messages = detail.map((item:ValidationIssue) => {
        const key = [...(item.loc || [])].reverse().find(x => typeof x === 'string' && x !== 'body');
        const field = fieldNames[String(key)] || (typeof key === 'string' ? key : 'campo');
        if (item.type === 'string_too_short') return `O campo ${field} deve conter pelo menos ${item.ctx?.min_length || 12} caracteres.`;
        if (item.type === 'string_too_long') return `O campo ${field} ultrapassou o limite de ${item.ctx?.max_length ?? 'tamanho'} caracteres.`;
        if (item.type === 'missing') return `Preencha o campo ${field}.`;
        if (item.type === 'value_error' && key === 'email') return 'Informe um endereço de e-mail válido.';
        if (item.type === 'string_pattern_mismatch') return `O campo ${field} está em formato inválido.`;
        if (item.type === 'value_error') return item.msg?.replace(/^Value error, /, '') || `Valor inválido em ${field}.`;
        return `Verifique o campo ${field}.`;
      });
      return [...new Set(messages)].join(' ') || 'Confira os campos preenchidos e tente novamente.';
    }
  }
  if (status === 422) return 'Confira os campos preenchidos e tente novamente.';
  if (status === 429) return 'Muitas solicitações. Aguarde e tente novamente.';
  return `Não foi possível concluir a solicitação (HTTP ${status}).`;
}
