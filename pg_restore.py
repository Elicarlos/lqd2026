
# Passos Restore Database Local
# del latest.dump
# heroku pg:backups:capture --app projetoliquida
# heroku pg:backups:download --app projetoliquida

#   pg_restore --verbose --clean --no-acl --no-owner -h localhost -U postgres -d nataldepremios latest.dump




del latest.dump
heroku pg:backups:capture --app npt2025
heroku pg:backups:download --app npt2025
pg_restore --verbose --clean --no-acl --no-owner -h localhost -p 5433 -U postgres -d npt2025_local latest.dump