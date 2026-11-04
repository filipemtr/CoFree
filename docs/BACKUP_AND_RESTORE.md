# Backup e restauração

Execute na raiz com o Compose ligado:

```bash
sh infrastructure/scripts/backup.sh
# Produz backups/cofree-AAAAMMDDTHHMMSSZ.dump (pg_dump formato custom)
sh infrastructure/scripts/restore.sh backups/cofree-AAAAMMDDTHHMMSSZ.dump
```

**Precauções:** arquivos dump contêm dados pessoais, hashes de autenticação e ciphertext; mantenha criptografados e restritos. Procedimento de restore é **destrutivo**: faça backup atual, pare API/workers antes de restaurar e valide o banco após. O script `pg_restore --clean --if-exists` não configura por si só um processo transacional de desastre.

**Recuperação de Vault:** backup de ciphertext não substitui a senha mestra nem a chave de recuperação do usuário. Não é possível restaurar credenciais em claro pelo backend.

Políticas de retenção, snapshots automatizados, replicação, criptografia automática de backups e simulações de restore estão pendentes. Não há validação real do script com PostgreSQL neste ambiente.
