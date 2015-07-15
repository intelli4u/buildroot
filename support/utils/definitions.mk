# Copyright (C) Intelli4u

_quota := "

define normalize-path
$(_quota)$(strip $(subst ",,$(1)))$(_quota)
endef
